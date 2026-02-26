from __future__ import annotations

import asyncio
import logging
import signal
import sys
import time
from collections.abc import AsyncIterator, Callable
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
from super_system.agents import build_agents
from super_system.cleanup import STALL_TIMEOUT_S, kill_descendant_processes
from super_system.config import load_api_key, load_skill_registries
from super_system.skills import SKILL_TOOL_NAMES, auto_discover, create_skills_mcp_server

_IS_WINDOWS = sys.platform == "win32"

logger = logging.getLogger("super_system.orchestrator")


class OrchestratorError(Exception):
    pass


class OrchestratorInterrupted(Exception):
    pass


@dataclass
class RunCallbacks:
    on_banner: Callable[..., Any] = field(default=lambda: None)
    on_text: Callable[..., Any] = field(default=lambda t: None)
    on_agent_dispatch: Callable[..., Any] = field(default=lambda a, d="": None)
    on_result: Callable[..., Any] = field(default=lambda *a, **kw: None)
    on_system: Callable[..., Any] = field(default=lambda s, d: None)
    on_interrupted: Callable[..., Any] = field(default=lambda: None)
    on_error: Callable[..., Any] = field(default=lambda m: None)


def console_callbacks() -> RunCallbacks:
    from super_system.console import (
        print_agent_dispatch,
        print_banner,
        print_error,
        print_interrupted,
        print_result,
        print_system,
        print_text,
    )

    return RunCallbacks(
        on_banner=print_banner,
        on_text=print_text,
        on_agent_dispatch=print_agent_dispatch,
        on_result=print_result,
        on_system=print_system,
        on_interrupted=print_interrupted,
        on_error=print_error,
    )


async def _as_stream(text: str) -> AsyncIterator[dict[str, Any]]:
    yield {
        "type": "user",
        "message": {"role": "user", "content": text},
        "parent_tool_use_id": None,
        "session_id": "",
    }


async def run(
    prompt: str,
    *,
    cwd: Path | None = None,
    verbose: bool = False,
    callbacks: RunCallbacks | None = None,
    handle_signals: bool = True,
) -> None:
    cb = callbacks or console_callbacks()
    cb.on_banner()

    loop = asyncio.get_running_loop()
    run_task = asyncio.current_task()
    interrupted = False

    if handle_signals:

        def _handle_signal(sig: int, _frame: object = None) -> None:
            nonlocal interrupted
            if interrupted:
                raise SystemExit(128 + sig)
            interrupted = True
            if run_task is not None:
                run_task.cancel()

        if _IS_WINDOWS:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _handle_signal, sig)

    effective_cwd = cwd or Path.cwd()
    api_key = load_api_key()
    registry_urls = load_skill_registries()

    try:
        installed = await auto_discover(
            prompt, effective_cwd, api_key=api_key, registry_urls=registry_urls
        )
        if installed:
            logger.info("Pre-session skill discovery installed: %s", installed)
    except Exception as exc:
        logger.warning("Pre-session skill discovery failed (continuing): %s", exc)

    agents = build_agents()
    skills_server = create_skills_mcp_server(
        cwd=effective_cwd, api_key=api_key, registry_urls=registry_urls
    )

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": prompts.ORCHESTRATOR,
        },
        allowed_tools=["Task", "Read", "Grep", "Glob"] + SKILL_TOOL_NAMES,
        agents=agents,
        permission_mode="bypassPermissions",
        model="opus",
        setting_sources=["user", "project"],
        mcp_servers={"skills": skills_server},
        extra_args={"chrome": None},
    )

    if cwd is not None:
        options.cwd = cwd
    if verbose:
        options.debug_stderr = sys.stderr

    last_activity = time.monotonic()
    stalled = False

    async def _watchdog() -> None:
        nonlocal stalled
        while True:
            await asyncio.sleep(30)
            idle = time.monotonic() - last_activity
            if idle > STALL_TIMEOUT_S:
                logger.warning(
                    "Pipeline stalled (no activity for %.0fs), interrupting",
                    idle,
                )
                stalled = True
                if run_task is not None:
                    run_task.cancel()
                return

    watchdog_task = asyncio.create_task(_watchdog())

    try:
        async for message in query(prompt=_as_stream(prompt), options=options):
            last_activity = time.monotonic()
            try:
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            cb.on_text(block.text)
                        elif isinstance(block, ToolUseBlock):
                            desc = ""
                            if isinstance(block.input, dict):
                                desc = block.input.get("description", "")
                            cb.on_agent_dispatch(block.name, desc)
                elif isinstance(message, ResultMessage):
                    cb.on_result(
                        message.num_turns,
                        message.total_cost_usd or 0,
                        message.duration_ms,
                        message.is_error,
                        str(message.result) if message.is_error else "",
                    )
                elif isinstance(message, SystemMessage):
                    if verbose:
                        cb.on_system(message.subtype, message.data)
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except Exception as exc:
                logger.warning("Error processing message: %s", exc, exc_info=True)
    except asyncio.CancelledError:
        if stalled:
            cb.on_error(
                "Pipeline stalled — no activity for "
                f"{STALL_TIMEOUT_S // 60} minutes. Interrupted automatically."
            )
        cb.on_interrupted()
        raise OrchestratorInterrupted() from None
    except KeyboardInterrupt:
        cb.on_interrupted()
        raise OrchestratorInterrupted() from None
    except BaseExceptionGroup as eg:
        cancelled, real = eg.split(
            lambda e: isinstance(e, (asyncio.CancelledError, KeyboardInterrupt))
        )
        if real is None:
            if stalled:
                cb.on_error(
                    "Pipeline stalled — no activity for "
                    f"{STALL_TIMEOUT_S // 60} minutes. Interrupted automatically."
                )
            cb.on_interrupted()
            raise OrchestratorInterrupted() from None
        for exc in real.exceptions:
            logger.warning("Agent error (ignored): %s: %s", type(exc).__name__, exc, exc_info=True)
            cb.on_error(f"{type(exc).__name__}: {exc}")
    except (OrchestratorInterrupted, OrchestratorError):
        raise
    except Exception as exc:
        logger.warning("Orchestrator error (ignored): %s", exc, exc_info=True)
        cb.on_error(str(exc) or type(exc).__name__)
    finally:
        watchdog_task.cancel()
        with suppress(asyncio.CancelledError):
            await watchdog_task
        kill_descendant_processes()
