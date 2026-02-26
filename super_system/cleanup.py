from __future__ import annotations

import atexit
import logging
import os
import signal
import subprocess
import sys
import time

logger = logging.getLogger("super_system.cleanup")

_registered = False
_main_pid: int | None = None

STALL_TIMEOUT_S = 600

_IS_WINDOWS = sys.platform == "win32"


def _get_descendant_pids(pid: int) -> list[int]:
    descendants: list[int] = []
    try:
        if _IS_WINDOWS:
            result = subprocess.run(
                [
                    "wmic", "process", "where",
                    f"ParentProcessId={pid}",
                    "get", "ProcessId",
                    "/format:value",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("ProcessId="):
                    val = line.split("=", 1)[1].strip()
                    if val.isdigit():
                        child_pid = int(val)
                        descendants.append(child_pid)
                        descendants.extend(_get_descendant_pids(child_pid))
        else:
            result = subprocess.run(
                ["pgrep", "-P", str(pid)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                stripped = line.strip()
                if stripped:
                    child_pid = int(stripped)
                    descendants.append(child_pid)
                    descendants.extend(_get_descendant_pids(child_pid))
    except Exception:
        pass
    return descendants


def kill_descendant_processes(pid: int | None = None) -> None:
    target = pid if pid is not None else _main_pid or os.getpid()
    descendants = _get_descendant_pids(target)
    if not descendants:
        return

    logger.debug(
        "Terminating %d descendant process(es): %s", len(descendants), descendants
    )

    if _IS_WINDOWS:
        for child_pid in reversed(descendants):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(child_pid)],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
    else:
        for child_pid in reversed(descendants):
            try:
                os.kill(child_pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass

        time.sleep(0.3)

        for child_pid in reversed(descendants):
            try:
                os.kill(child_pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


def has_active_descendants(pid: int | None = None) -> bool:
    target = pid if pid is not None else _main_pid or os.getpid()
    return len(_get_descendant_pids(target)) > 0


def register_cleanup() -> None:
    global _registered, _main_pid
    if _registered:
        return
    _registered = True
    _main_pid = os.getpid()
    atexit.register(kill_descendant_processes)
