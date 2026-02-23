from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

from super_system.console import (
    err_console,
    print_error,
    print_interrupted,
    print_intake_banner,
    print_intake_crafted,
    print_intake_tool_use,
    print_text,
    prompt_user_input,
)
from super_system.intake import IntakeCallbacks, IntakeError, IntakeInterrupted, run_intake
from super_system.orchestrator import OrchestratorError, OrchestratorInterrupted, run


def main() -> None:
    from super_system.cleanup import register_cleanup

    register_cleanup()

    parser = argparse.ArgumentParser(
        description="Multi-agent software engineering team powered by Claude",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default=None,
        help="Project description to build (reads from stdin if omitted)",
    )
    parser.add_argument(
        "-C",
        "--cwd",
        type=Path,
        default=None,
        help="Working directory for the agents (defaults to current directory)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Use plain console output instead of the interactive TUI",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Skip the intake agent and pass the prompt directly to the orchestrator",
    )
    args = parser.parse_args()

    prompt: str | None = args.prompt
    if prompt is None and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()

    cwd: Path | None = args.cwd
    if cwd is not None:
        cwd = cwd.resolve()
        if not cwd.is_dir():
            parser.error(f"Working directory does not exist: {cwd}")

    if args.no_tui:
        if not prompt:
            parser.error("No prompt provided. Pass as argument or pipe via stdin.")
        _run_console(prompt, cwd=cwd, verbose=args.verbose, direct=args.direct)
    else:
        _run_tui(prompt or None, cwd=cwd, verbose=args.verbose, direct=args.direct)


def _run_console(
    prompt: str,
    *,
    cwd: Path | None,
    verbose: bool,
    direct: bool,
) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=err_console,
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        ],
    )

    final_prompt = prompt

    if not direct:
        try:
            print_intake_banner()
            final_prompt = asyncio.run(
                run_intake(
                    prompt,
                    cwd=cwd,
                    verbose=verbose,
                    callbacks=IntakeCallbacks(
                        on_text=print_text,
                        on_tool_use=print_intake_tool_use,
                        get_user_input=prompt_user_input,
                        on_crafted=print_intake_crafted,
                        on_interrupted=print_interrupted,
                        on_error=print_error,
                    ),
                )
            )
        except IntakeInterrupted:
            raise SystemExit(130)
        except IntakeError as exc:
            print_error(str(exc))
            raise SystemExit(1)
        except KeyboardInterrupt:
            print_interrupted()
            raise SystemExit(130)

    try:
        asyncio.run(
            run(
                final_prompt,
                cwd=cwd,
                verbose=verbose,
            )
        )
    except OrchestratorInterrupted:
        raise SystemExit(130)
    except OrchestratorError:
        raise SystemExit(1)
    except KeyboardInterrupt:
        print_interrupted()
        raise SystemExit(130)
    except SystemExit:
        raise
    except BaseExceptionGroup as eg:
        _, real = eg.split(
            lambda e: isinstance(e, (asyncio.CancelledError, KeyboardInterrupt))
        )
        if real is None:
            print_interrupted()
            raise SystemExit(130)
        for sub in real.exceptions:
            print_error(f"{type(sub).__name__}: {sub}")
        raise SystemExit(1) from real
    except Exception as exc:
        print_error(str(exc) or type(exc).__name__)
        raise SystemExit(1) from exc


def _run_tui(
    prompt: str | None,
    *,
    cwd: Path | None,
    verbose: bool,
    direct: bool,
) -> None:
    from super_system.tui import SuperSystemApp

    app = SuperSystemApp(
        prompt,
        cwd=cwd,
        verbose=verbose,
        direct=direct,
    )
    app.run()
