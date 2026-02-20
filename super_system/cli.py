from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.logging import RichHandler
from rich.table import Table

from super_system.console import err_console, print_error, print_interrupted
from super_system.orchestrator import OrchestratorError, OrchestratorInterrupted, run


def _list_sessions() -> None:
    from super_system.sessions import list_sessions

    sessions = list_sessions()
    if not sessions:
        err_console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(title="Sessions", show_lines=False, expand=False)
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Prompt", style="white", max_width=50)
    table.add_column("Status", style="bold")
    table.add_column("Turns", justify="right")
    table.add_column("Cost", justify="right")
    table.add_column("Started", style="dim")

    for s in reversed(sessions):
        status_style = {
            "completed": "green",
            "running": "yellow",
            "failed": "red",
            "interrupted": "yellow",
        }.get(s.status, "white")

        started = datetime.fromtimestamp(s.started_at, tz=timezone.utc).astimezone().strftime(
            "%Y-%m-%d %H:%M"
        )

        table.add_row(
            s.session_id[:16],
            s.prompt_preview[:50],
            f"[{status_style}]{s.status}[/{status_style}]",
            str(s.num_turns),
            f"${s.cost_usd:.4f}",
            started,
        )

    err_console.print(table)


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
        "--resume",
        type=str,
        default=None,
        metavar="SESSION_ID",
        help="Resume a previous session by ID (supports prefix matching)",
    )
    parser.add_argument(
        "--fork",
        action="store_true",
        help="Fork the session when resuming instead of continuing it",
    )
    parser.add_argument(
        "--sessions",
        action="store_true",
        help="List past sessions and exit",
    )
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Use plain console output instead of the interactive TUI",
    )
    args = parser.parse_args()

    if args.sessions:
        _list_sessions()
        return

    if args.fork and not args.resume:
        parser.error("--fork requires --resume SESSION_ID")

    if args.resume:
        from super_system.sessions import get_session

        record = get_session(args.resume)
        if record:
            args.resume = record.session_id

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
        _run_console(prompt, cwd=cwd, verbose=args.verbose, resume=args.resume, fork=args.fork)
    else:
        if not prompt and args.resume:
            prompt = "Continue from where you left off."
        _run_tui(prompt or None, cwd=cwd, verbose=args.verbose, resume=args.resume, fork=args.fork)


def _run_console(
    prompt: str,
    *,
    cwd: Path | None,
    verbose: bool,
    resume: str | None,
    fork: bool,
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
                resume=resume,
                fork_session=fork,
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
    resume: str | None,
    fork: bool,
) -> None:
    from super_system.tui import SuperSystemApp

    app = SuperSystemApp(
        prompt,
        cwd=cwd,
        verbose=verbose,
        resume=resume,
        fork_session=fork,
    )
    app.run()
