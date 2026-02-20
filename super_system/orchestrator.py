from __future__ import annotations

import asyncio
import signal
import sys
from collections.abc import AsyncIterator, Callable
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
    interrupted = False

    if handle_signals:

        def _handle_signal(sig: int, _frame: object = None) -> None:
            nonlocal interrupted
            if interrupted:
                raise SystemExit(128 + sig)
            interrupted = True
            for task in asyncio.all_tasks(loop):
                task.cancel()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _handle_signal, sig)

    agents = build_agents()

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": prompts.ORCHESTRATOR,
        },
        allowed_tools=["Task", "Read", "Grep", "Glob"],
        agents=agents,
        permission_mode="bypassPermissions",
        model="opus",
        extra_args={"chrome": None},
    )

    if cwd is not None:
        options.cwd = cwd
    if verbose:
        options.debug_stderr = sys.stderr

    try:
        async for message in query(prompt=_as_stream(prompt), options=options):
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
    except asyncio.CancelledError:
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
            cb.on_interrupted()
            raise OrchestratorInterrupted() from None
        for exc in real.exceptions:
            cb.on_error(f"{type(exc).__name__}: {exc}")
        raise OrchestratorError(str(real)) from real
    except (OrchestratorInterrupted, OrchestratorError):
        raise
    except Exception as exc:
        cb.on_error(str(exc) or type(exc).__name__)
        raise OrchestratorError(str(exc)) from exc
