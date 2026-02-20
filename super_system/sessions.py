from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

_SESSIONS_DIR = Path.home() / ".config" / "super-system"
_SESSIONS_FILE = _SESSIONS_DIR / "sessions.json"


@dataclass
class SessionRecord:
    session_id: str
    prompt_preview: str
    started_at: float
    status: str = "running"
    cost_usd: float = 0.0
    num_turns: int = 0
    duration_ms: int = 0


def _load_records() -> list[dict]:
    if not _SESSIONS_FILE.exists():
        return []
    try:
        return json.loads(_SESSIONS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _save_records(records: list[dict]) -> None:
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _SESSIONS_FILE.write_text(json.dumps(records, indent=2))


def save_session(record: SessionRecord) -> None:
    records = _load_records()
    for i, r in enumerate(records):
        if r.get("session_id") == record.session_id:
            records[i] = asdict(record)
            _save_records(records)
            return
    records.append(asdict(record))
    _save_records(records)


def list_sessions() -> list[SessionRecord]:
    return [SessionRecord(**r) for r in _load_records()]


def get_session(session_id: str) -> SessionRecord | None:
    for r in _load_records():
        sid = r.get("session_id", "")
        if sid == session_id or sid.startswith(session_id):
            return SessionRecord(**r)
    return None
