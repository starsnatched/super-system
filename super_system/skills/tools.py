from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from super_system.skills.manager import install, list_installed
from super_system.skills.registry import SkillRegistryAggregator

_cwd: Path = Path.cwd()
_api_key: str = ""
_registry_urls: list[str] = []


def configure(
    cwd: Path,
    api_key: str = "",
    registry_urls: list[str] | None = None,
) -> None:
    global _cwd, _api_key, _registry_urls
    _cwd = cwd
    _api_key = api_key
    _registry_urls = registry_urls or []


def _aggregator() -> SkillRegistryAggregator:
    return SkillRegistryAggregator(
        api_key=_api_key,
        registry_urls=_registry_urls,
    )


@tool(
    "search_skills",
    (
        "Search for available skills by keyword across all configured registries "
        "(Anthropic marketplace and HTTP registries). Returns matching skills with "
        "their IDs, names, descriptions, and sources."
    ),
    {"query": str},
)
async def search_skills(args: dict[str, Any]) -> dict[str, Any]:
    query = args["query"]
    agg = _aggregator()
    results = await agg.search(query)
    items = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "source": s.source,
            "has_download": bool(s.download_url),
        }
        for s in results
    ]
    text = json.dumps(items, indent=2) if items else "No skills found matching the query."
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "install_skill",
    (
        "Install a skill by searching for it and downloading its SKILL.md to the "
        "project's .claude/skills/ directory. Provide a search query to find and "
        "install the best matching skill. The skill becomes available to agents "
        "via the Skill tool, or agents can read .claude/skills/<name>/SKILL.md directly."
    ),
    {"query": str},
)
async def install_skill(args: dict[str, Any]) -> dict[str, Any]:
    query = args["query"]
    agg = _aggregator()
    results = await agg.search(query)

    installable = [s for s in results if s.download_url]
    if not installable:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"No installable skills found for query: {query}",
                }
            ]
        }

    skill = installable[0]
    path = await install(skill, _cwd)
    if path:
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Installed skill '{skill.name}' to {path}. "
                        f"Agents can use it via the Skill tool, or read "
                        f"{path / 'SKILL.md'} directly."
                    ),
                }
            ]
        }
    return {
        "content": [
            {
                "type": "text",
                "text": f"Failed to install skill '{skill.name}'. Check logs for details.",
            }
        ]
    }


@tool(
    "list_installed_skills",
    (
        "List all skills currently installed in the project's .claude/skills/ directory. "
        "Returns skill names, descriptions, and file paths."
    ),
    {},
)
async def list_installed_skills(args: dict[str, Any]) -> dict[str, Any]:
    installed = list_installed(_cwd)
    if not installed:
        return {"content": [{"type": "text", "text": "No skills currently installed."}]}
    text = json.dumps(installed, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def create_skills_mcp_server(
    cwd: Path,
    api_key: str = "",
    registry_urls: list[str] | None = None,
):
    configure(cwd=cwd, api_key=api_key, registry_urls=registry_urls)
    return create_sdk_mcp_server(
        name="skills",
        tools=[search_skills, install_skill, list_installed_skills],
    )


SKILL_TOOL_NAMES = [
    "mcp__skills__search_skills",
    "mcp__skills__install_skill",
    "mcp__skills__list_installed_skills",
]
