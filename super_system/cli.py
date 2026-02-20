from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

from super_system.console import err_console, print_error, print_interrupted
from super_system.orchestrator import OrchestratorError, OrchestratorInterrupted, run


def main() -> None:
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
        _run_console(prompt, cwd=cwd, verbose=args.verbose)
    else:
        _run_tui(prompt or None, cwd=cwd, verbose=args.verbose)


def _run_console(
    prompt: str,
    *,
    cwd: Path | None,
    verbose: bool,
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

    try:
        asyncio.run(
            run(
                prompt,
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
) -> None:
    from super_system.tui import SuperSystemApp

    app = SuperSystemApp(
        prompt,
        cwd=cwd,
        verbose=verbose,
    )
    app.run()
