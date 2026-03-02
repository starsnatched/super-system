from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path

import httpx

from super_system.skills.registry import SkillInfo, SkillRegistryAggregator

logger = logging.getLogger("super_system.skills.manager")

_HTTP_TIMEOUT = 30.0
_RELEVANCE_THRESHOLD = 0.4
_BUNDLED_DIR = Path(__file__).parent / "bundled"


def _skills_dir(cwd: Path) -> Path:
    return cwd / ".claude" / "skills"


def ensure_bundled_skills(cwd: Path) -> list[str]:
    installed: list[str] = []
    if not _BUNDLED_DIR.is_dir():
        return installed

    target_base = _skills_dir(cwd)
    for entry in sorted(_BUNDLED_DIR.iterdir()):
        if not entry.is_dir():
            continue
        src = entry / "SKILL.md"
        if not src.is_file():
            continue
        dest_dir = target_base / entry.name
        dest_file = dest_dir / "SKILL.md"
        if dest_file.is_file():
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_file)
        logger.info("Deployed bundled skill %s to %s", entry.name, dest_file)
        installed.append(entry.name)

    return installed


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        kv = line.split(":", 1)
        if len(kv) == 2:
            key = kv[0].strip()
            val = kv[1].strip().strip("\"'")
            if key:
                result[key] = val
    return result


def _validate_skill_md(content: str) -> bool:
    fm = _parse_frontmatter(content)
    return bool(fm.get("name")) and bool(fm.get("description"))


async def install(skill: SkillInfo, cwd: Path) -> Path | None:
    if not skill.download_url:
        logger.warning("Skill %s has no download_url, skipping install", skill.id)
        return None

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(skill.download_url)
            resp.raise_for_status()
            content = resp.text
    except httpx.HTTPError as exc:
        logger.warning("Failed to download skill %s: %s", skill.id, exc)
        return None

    if not _validate_skill_md(content):
        logger.warning(
            "Skill %s: downloaded content is not a valid SKILL.md (missing name/description frontmatter)",
            skill.id,
        )
        return None

    safe_name = re.sub(r"[^a-z0-9_-]", "-", skill.name.lower().strip())
    if not safe_name:
        safe_name = re.sub(r"[^a-z0-9_-]", "-", skill.id.lower().strip())

    skill_path = _skills_dir(cwd) / safe_name
    skill_path.mkdir(parents=True, exist_ok=True)
    skill_file = skill_path / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    logger.info("Installed skill %s to %s", skill.name, skill_file)
    return skill_path


def list_installed(cwd: Path) -> list[dict[str, str]]:
    base = _skills_dir(cwd)
    if not base.is_dir():
        return []

    installed: list[dict[str, str]] = []
    for entry in sorted(base.iterdir()):
        skill_file = entry / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            text = skill_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        installed.append(
            {
                "directory": entry.name,
                "name": fm.get("name", entry.name),
                "description": fm.get("description", ""),
                "path": str(skill_file),
            }
        )
    return installed


def uninstall(name: str, cwd: Path) -> bool:
    base = _skills_dir(cwd)
    target = base / name
    if not target.is_dir():
        return False
    shutil.rmtree(target)
    logger.info("Uninstalled skill %s", name)
    return True


async def auto_discover(
    prompt: str,
    cwd: Path,
    api_key: str = "",
    registry_urls: list[str] | None = None,
) -> list[str]:
    cwd = cwd or Path.cwd()

    aggregator = SkillRegistryAggregator(
        api_key=api_key,
        registry_urls=registry_urls,
    )

    results = await aggregator.search(prompt)
    if not results:
        logger.debug("auto_discover: no skills matched prompt")
        return []

    already = {s["name"] for s in list_installed(cwd)}
    installed_names: list[str] = []

    for skill in results:
        if skill.matches(prompt) < _RELEVANCE_THRESHOLD:
            continue
        if skill.name in already:
            logger.debug("auto_discover: %s already installed", skill.name)
            continue
        if not skill.download_url:
            continue
        path = await install(skill, cwd)
        if path:
            installed_names.append(skill.name)

    if installed_names:
        logger.info("auto_discover installed %d skills: %s", len(installed_names), installed_names)
    return installed_names
