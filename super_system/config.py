from __future__ import annotations

import json
from pathlib import Path

_CONFIG_DIR = Path.home() / ".config" / "super-system"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def _load_config() -> dict:
    if not _CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_config(config: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_api_key() -> str:
    return _load_config().get("api_key", "")


def save_api_key(key: str) -> None:
    config = _load_config()
    config["api_key"] = key
    _save_config(config)


def load_skill_registries() -> list[str]:
    return _load_config().get("skill_registries", [])


def save_skill_registries(urls: list[str]) -> None:
    config = _load_config()
    config["skill_registries"] = urls
    _save_config(config)
