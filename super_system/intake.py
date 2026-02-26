from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from collections.abc import AsyncIterator, Callable, Awaitable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from super_system import prompts
from super_system.agents import BROWSER_TOOLS
from super_system.cleanup import STALL_TIMEOUT_S, has_active_descendants, kill_descendant_processes

_IS_WINDOWS = sys.platform == "win32"

logger = logging.getLogger("super_system.intake")

MAX_CONVERSATION_TURNS = 15


async def _noop_get_input() -> str | None:
    return None


class IntakeInterrupted(Exception):
    pass


class IntakeError(Exception):
    pass


@dataclass
class IntakeCallbacks:
    on_text: Callable[[str], Any] = field(default=lambda t: None)
    on_tool_use: Callable[[str, str], Any] = field(default=lambda n, d="": None)
    get_user_input: Callable[[], Awaitable[str | None]] = field(
        default=lambda: _noop_get_input()
    )
    on_crafted: Callable[[str], Any] = field(default=lambda p: None)
    on_interrupted: Callable[[], Any] = field(default=lambda: None)
    on_error: Callable[[str], Any] = field(default=lambda m: None)


async def _as_stream(text: str) -> AsyncIterator[dict[str, Any]]:
    yield {
        "type": "user",
        "message": {"role": "user", "content": text},
        "parent_tool_use_id": None,
        "session_id": "",
    }


def _build_options(
    *,
    session_id: str | None,
    cwd: Path | None,
    verbose: bool,
) -> ClaudeAgentOptions:
    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": prompts.INTAKE,
        },
        allowed_tools=[
            "Read", "Grep", "Glob", "WebSearch", "WebFetch",
        ] + BROWSER_TOOLS,
        permission_mode="bypassPermissions",
        model="opus",
        extra_args={"chrome": None},
    )

    if session_id is not None:
        options.resume = session_id

    if cwd is not None:
        options.cwd = cwd

    if verbose:
        options.debug_stderr = sys.stderr

    return options


async def _run_turn(
    prompt_text: str,
    *,
    session_id: str | None,
    cwd: Path | None,
    verbose: bool,
    cb: IntakeCallbacks,
) -> tuple[str, str | None]:
    options = _build_options(
        session_id=session_id,
        cwd=cwd,
        verbose=verbose,
    )

    collected_text: list[str] = []
    captured_session_id = session_id
    last_activity = time.monotonic()
    parent_task = asyncio.current_task()

    async def _watchdog() -> None:
        nonlocal last_activity
        while True:
            await asyncio.sleep(30)
            idle = time.monotonic() - last_activity
            if idle > STALL_TIMEOUT_S:
                if has_active_descendants():
                    logger.debug(
                        "No stream activity for %.0fs but descendant processes "
                        "still running — resetting stall timer",
                        idle,
                    )
                    last_activity = time.monotonic()
                    continue
                logger.warning(
                    "Intake stalled (no activity for %.0fs), interrupting",
                    idle,
                )
                if parent_task is not None:
                    parent_task.cancel()
                return

    watchdog_task = asyncio.create_task(_watchdog())

    try:
        async for message in query(prompt=_as_stream(prompt_text), options=options):
            last_activity = time.monotonic()
            try:
                if isinstance(message, SystemMessage):
                    if hasattr(message, "subtype") and message.subtype == "init":
                        sid = (
                            message.data.get("session_id")
                            if isinstance(message.data, dict)
                            else None
                        )
                        if sid:
                            captured_session_id = sid
                elif isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            collected_text.append(block.text)
                            cb.on_text(block.text)
                        elif isinstance(block, ToolUseBlock):
                            desc = ""
                            if isinstance(block.input, dict):
                                desc = block.input.get("description", "")
                            cb.on_tool_use(block.name, desc)
                elif isinstance(message, ResultMessage):
                    if message.is_error:
                        logger.warning("Intake turn error: %s", message.result)
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except Exception as exc:
                logger.warning("Error processing intake message: %s", exc, exc_info=True)
    finally:
        watchdog_task.cancel()
        with suppress(asyncio.CancelledError):
            await watchdog_task

    return "\n".join(collected_text), captured_session_id


async def run_intake(
    initial_prompt: str,
    *,
    cwd: Path | None = None,
    verbose: bool = False,
    callbacks: IntakeCallbacks | None = None,
    handle_signals: bool = True,
) -> str:
    cb = callbacks or IntakeCallbacks()

    loop = asyncio.get_running_loop()
    intake_task = asyncio.current_task()
    interrupted = False

    if handle_signals:

        def _handle_signal(sig: int, _frame: object = None) -> None:
            nonlocal interrupted
            if interrupted:
                raise SystemExit(128 + sig)
            interrupted = True
            if intake_task is not None:
                intake_task.cancel()

        if _IS_WINDOWS:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _handle_signal, sig)

    session_id: str | None = None
    last_response = ""

    try:
        for turn in range(MAX_CONVERSATION_TURNS):
            prompt_text = initial_prompt if turn == 0 else user_reply  # type: ignore[possibly-undefined]

            last_response, session_id = await _run_turn(
                prompt_text,
                session_id=session_id,
                cwd=cwd,
                verbose=verbose,
                cb=cb,
            )

            user_reply_raw = await cb.get_user_input()
            if user_reply_raw is None or not user_reply_raw.strip():
                break

            user_reply = user_reply_raw.strip()

        if not last_response.strip():
            raise IntakeError(
                "Intake agent did not produce any output."
            )

        cb.on_crafted(last_response)
        return last_response

    except asyncio.CancelledError:
        cb.on_interrupted()
        raise IntakeInterrupted() from None
    except KeyboardInterrupt:
        cb.on_interrupted()
        raise IntakeInterrupted() from None
    except BaseExceptionGroup as eg:
        _, real = eg.split(
            lambda e: isinstance(e, (asyncio.CancelledError, KeyboardInterrupt))
        )
        if real is None:
            cb.on_interrupted()
            raise IntakeInterrupted() from None
        for exc in real.exceptions:
            logger.warning(
                "Intake error: %s: %s", type(exc).__name__, exc, exc_info=True
            )
            cb.on_error(f"{type(exc).__name__}: {exc}")
        raise IntakeError("Intake failed due to errors") from real
    except (IntakeInterrupted, IntakeError):
        raise
    except Exception as exc:
        logger.warning("Intake error: %s", exc, exc_info=True)
        cb.on_error(str(exc) or type(exc).__name__)
        raise IntakeError(str(exc)) from exc
    finally:
        kill_descendant_processes()
