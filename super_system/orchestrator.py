import asyncio
import signal
import sys
from collections.abc import AsyncIterator
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
from super_system.console import (
    print_agent_dispatch,
    print_artifact_shared,
    print_banner,
    print_error,
    print_interrupted,
    print_message_activity,
    print_result,
    print_system,
    print_text,
)
from super_system.message_board import (
    COMMS_TOOLS,
    MessageBoard,
    build_message_board_server,
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
) -> None:
    print_banner()

    loop = asyncio.get_running_loop()
    interrupted = False

    def _handle_signal(sig: int, _frame: object = None) -> None:
        nonlocal interrupted
        if interrupted:
            raise SystemExit(128 + sig)
        interrupted = True
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    board = MessageBoard()
    board.on_message(print_message_activity)
    board.on_artifact(
        lambda owner, key, _content: print_artifact_shared(owner, key)
    )

    mcp_server = build_message_board_server(board)

    agents = build_agents()

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": prompts.ORCHESTRATOR,
        },
        allowed_tools=["Task", "Read", "Grep", "Glob"] + COMMS_TOOLS,
        agents=agents,
        mcp_servers={"message-board": mcp_server},
        permission_mode="bypassPermissions",
        extra_args={"--chrome": None},
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
                        print_text(block.text)
                    elif isinstance(block, ToolUseBlock):
                        desc = ""
                        if isinstance(block.input, dict):
                            desc = block.input.get("description", "")
                        print_agent_dispatch(block.name, desc)
            elif isinstance(message, ResultMessage):
                print_result(
                    num_turns=message.num_turns,
                    cost_usd=message.total_cost_usd or 0,
                    duration_ms=message.duration_ms,
                    is_error=message.is_error,
                    error_text=str(message.result) if message.is_error else "",
                )
            elif isinstance(message, SystemMessage):
                if verbose:
                    print_system(message.subtype, message.data)
    except asyncio.CancelledError:
        print_interrupted()
        raise SystemExit(130)
    except KeyboardInterrupt:
        print_interrupted()
        raise SystemExit(130)
    except BaseExceptionGroup as eg:
        cancelled, real = eg.split(
            lambda e: isinstance(e, (asyncio.CancelledError, KeyboardInterrupt))
        )
        if real is None:
            print_interrupted()
            raise SystemExit(130)
        for exc in real.exceptions:
            print_error(f"{type(exc).__name__}: {exc}")
        raise SystemExit(1) from real
    except Exception as exc:
        print_error(str(exc) or type(exc).__name__)
        raise SystemExit(1) from exc
