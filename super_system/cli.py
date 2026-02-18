import argparse
import asyncio
import logging
import sys
from pathlib import Path

from rich.logging import RichHandler

from super_system.console import print_error, print_interrupted
from super_system.orchestrator import run


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
    args = parser.parse_args()

    prompt: str = args.prompt or sys.stdin.read().strip()
    if not prompt:
        parser.error("No prompt provided. Pass as argument or pipe via stdin.")

    cwd: Path | None = args.cwd
    if cwd is not None:
        cwd = cwd.resolve()
        if not cwd.is_dir():
            parser.error(f"Working directory does not exist: {cwd}")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        ],
    )

    try:
        asyncio.run(run(prompt, cwd=cwd, verbose=args.verbose))
    except KeyboardInterrupt:
        print_interrupted()
        raise SystemExit(130)
    except SystemExit as exc:
        raise exc
    except Exception as exc:
        print_error(str(exc) or type(exc).__name__)
        raise SystemExit(1) from exc
