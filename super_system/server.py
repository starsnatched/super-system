from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from super_system.orchestrator import (
    OrchestratorError,
    OrchestratorInterrupted,
    RunCallbacks,
    run,
)
from super_system.sessions import list_sessions, save_session, SessionRecord

logger = logging.getLogger("super_system.server")

app = FastAPI(title="super-system", version="0.1.0")

_running_task: asyncio.Task[None] | None = None
_running_ws: WebSocket | None = None


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sessions")
async def get_sessions() -> JSONResponse:
    sessions = list_sessions()
    return JSONResponse([asdict(s) for s in sessions])


@app.post("/api/sessions/{session_id}/interrupt")
async def interrupt_session(session_id: str) -> dict[str, str]:
    global _running_task
    if _running_task is not None and not _running_task.done():
        _running_task.cancel()
        return {"status": "interrupted"}
    return {"status": "no_running_session"}


async def _send(ws: WebSocket, event: dict[str, Any]) -> None:
    try:
        await ws.send_json(event)
    except Exception:
        pass


async def _run_session(
    ws: WebSocket,
    prompt: str,
    cwd: str,
    resume: str | None,
    fork: bool,
) -> None:
    global _running_task, _running_ws
    _running_ws = ws

    session_id: str | None = None
    start_wall = time.time()

    def on_text(text: str) -> None:
        asyncio.get_event_loop().create_task(
            _send(ws, {"type": "text", "content": text})
        )

    def on_agent_dispatch(agent_name: str, description: str = "") -> None:
        asyncio.get_event_loop().create_task(
            _send(ws, {"type": "agent_dispatch", "agent": agent_name, "description": description})
        )

    def on_result(
        num_turns: int,
        cost_usd: float,
        duration_ms: int,
        is_error: bool = False,
        error_text: str = "",
    ) -> None:
        asyncio.get_event_loop().create_task(
            _send(ws, {
                "type": "result",
                "turns": num_turns,
                "cost": cost_usd,
                "duration_ms": duration_ms,
                "is_error": is_error,
                "error_text": error_text,
            })
        )
        if session_id:
            save_session(SessionRecord(
                session_id=session_id,
                prompt_preview=prompt[:100],
                started_at=start_wall,
                status="failed" if is_error else "completed",
                cost_usd=cost_usd,
                num_turns=num_turns,
                duration_ms=duration_ms,
            ))

    def on_session_id(sid: str) -> None:
        nonlocal session_id
        session_id = sid
        asyncio.get_event_loop().create_task(
            _send(ws, {"type": "session_id", "id": sid})
        )
        save_session(SessionRecord(
            session_id=sid,
            prompt_preview=prompt[:100],
            started_at=start_wall,
            status="running",
        ))

    def on_interrupted() -> None:
        asyncio.get_event_loop().create_task(
            _send(ws, {"type": "interrupted"})
        )
        if session_id:
            save_session(SessionRecord(
                session_id=session_id,
                prompt_preview=prompt[:100],
                started_at=start_wall,
                status="interrupted",
            ))

    def on_error(message: str) -> None:
        asyncio.get_event_loop().create_task(
            _send(ws, {"type": "error", "message": message})
        )
        if session_id:
            save_session(SessionRecord(
                session_id=session_id,
                prompt_preview=prompt[:100],
                started_at=start_wall,
                status="failed",
            ))

    callbacks = RunCallbacks(
        on_banner=lambda: None,
        on_text=on_text,
        on_agent_dispatch=on_agent_dispatch,
        on_result=on_result,
        on_system=lambda s, d: None,
        on_session_id=on_session_id,
        on_interrupted=on_interrupted,
        on_error=on_error,
    )

    cwd_path = Path(cwd).resolve() if cwd else None

    try:
        await run(
            prompt,
            cwd=cwd_path,
            verbose=False,
            resume=resume,
            fork_session=fork,
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
                    await _send(ws, {"type": "error", "message": "A session is already running."})
                    continue

                prompt = data.get("prompt", "")
                cwd = data.get("cwd", "")
                resume = data.get("resume")
                fork = data.get("fork", False)

                if not prompt:
                    await _send(ws, {"type": "error", "message": "No prompt provided."})
                    continue
                if not cwd:
                    await _send(ws, {"type": "error", "message": "No working directory provided."})
                    continue

                _running_task = asyncio.create_task(
                    _run_session(ws, prompt, cwd, resume, fork)
                )

            elif msg_type == "interrupt":
                if _running_task is not None and not _running_task.done():
                    _running_task.cancel()
                else:
                    await _send(ws, {"type": "error", "message": "No session to interrupt."})

    except WebSocketDisconnect:
        if _running_task is not None and not _running_task.done():
            _running_task.cancel()
    except Exception:
        if _running_task is not None and not _running_task.done():
            _running_task.cancel()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    uvicorn.run(app, host="127.0.0.1", port=9810, log_level="info")


if __name__ == "__main__":
    main()
