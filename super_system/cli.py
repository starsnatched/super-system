import argparse
import asyncio
import logging
import sys
from pathlib import Path

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
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(run(prompt, cwd=cwd, verbose=args.verbose))
