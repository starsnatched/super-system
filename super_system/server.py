from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from super_system.cleanup import kill_descendant_processes, register_cleanup
from super_system.orchestrator import (
    OrchestratorError,
    OrchestratorInterrupted,
    RunCallbacks,
    run,
)

logger = logging.getLogger("super_system.server")


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    kill_descendant_processes()


app = FastAPI(title="super-system", version="0.1.0", lifespan=_lifespan)

_running_task: asyncio.Task[None] | None = None
_running_ws: WebSocket | None = None


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/interrupt")
async def interrupt() -> dict[str, str]:
    global _running_task
    if _running_task is not None and not _running_task.done():
        _running_task.cancel()
        return {"status": "interrupted"}
    return {"status": "nothing_running"}


async def _send(ws: WebSocket, event: dict[str, Any]) -> None:
    try:
        await ws.send_json(event)
    except Exception:
        pass


async def _run_task(
    ws: WebSocket,
    prompt: str,
    cwd: str,
) -> None:
    global _running_task, _running_ws
    _running_ws = ws
    loop = asyncio.get_running_loop()

    def on_text(text: str) -> None:
        loop.create_task(
            _send(ws, {"type": "text", "content": text})
        )

    def on_agent_dispatch(agent_name: str, description: str = "") -> None:
        loop.create_task(
            _send(ws, {"type": "agent_dispatch", "agent": agent_name, "description": description})
        )

    def on_result(
        num_turns: int,
        cost_usd: float,
        duration_ms: int,
        is_error: bool = False,
        error_text: str = "",
    ) -> None:
        loop.create_task(
            _send(ws, {
                "type": "result",
                "turns": num_turns,
                "cost": cost_usd,
                "duration_ms": duration_ms,
                "is_error": is_error,
                "error_text": error_text,
            })
        )

    def on_interrupted() -> None:
        loop.create_task(
            _send(ws, {"type": "interrupted"})
        )

    def on_error(message: str) -> None:
        loop.create_task(
            _send(ws, {"type": "error", "message": message})
        )

    callbacks = RunCallbacks(
        on_banner=lambda: None,
        on_text=on_text,
        on_agent_dispatch=on_agent_dispatch,
        on_result=on_result,
        on_system=lambda s, d: None,
        on_interrupted=on_interrupted,
        on_error=on_error,
    )

    cwd_path = Path(cwd).resolve() if cwd else None

    try:
        await run(
            prompt,
            cwd=cwd_path,
            verbose=False,
            callbacks=callbacks,
            handle_signals=False,
        )
    except OrchestratorInterrupted:
        pass
    except OrchestratorError:
        pass
    except asyncio.CancelledError:
        on_interrupted()
    except Exception as exc:
        on_error(f"{type(exc).__name__}: {exc}")
    finally:
        _running_task = None
        _running_ws = None


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    global _running_task
    await ws.accept()

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type")

            if msg_type == "start":
                if _running_task is not None and not _running_task.done():
                    await _send(ws, {"type": "error", "message": "A task is already running."})
                    continue

                prompt = data.get("prompt", "")
                cwd = data.get("cwd", "")

                if not prompt:
                    await _send(ws, {"type": "error", "message": "No prompt provided."})
                    continue
                if not cwd:
                    await _send(ws, {"type": "error", "message": "No working directory provided."})
                    continue

                _running_task = asyncio.create_task(
                    _run_task(ws, prompt, cwd)
                )

            elif msg_type == "interrupt":
                if _running_task is not None and not _running_task.done():
                    _running_task.cancel()
                else:
                    await _send(ws, {"type": "error", "message": "Nothing to interrupt."})

    except WebSocketDisconnect:
        if _running_task is not None and not _running_task.done():
            _running_task.cancel()
    except Exception:
        if _running_task is not None and not _running_task.done():
            _running_task.cancel()


def main() -> None:
    register_cleanup()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    uvicorn.run(app, host="127.0.0.1", port=9810, log_level="info")


if __name__ == "__main__":
    main()
