from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("super_system.skills.registry")

_SKILLS_BETA = "skills-2025-10-02"
_ANTHROPIC_API_BASE = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"
_HTTP_TIMEOUT = 30.0


@dataclass(frozen=True)
class SkillInfo:
    id: str
    name: str
    description: str
    source: str
    download_url: str = ""
    version: str = ""
    tags: list[str] = field(default_factory=list)

    def matches(self, query: str) -> float:
        query_lower = query.lower()
        tokens = re.split(r"\s+", query_lower)
        searchable = f"{self.name} {self.description} {' '.join(self.tags)}".lower()
        hits = sum(1 for t in tokens if t in searchable)
        if not tokens:
            return 0.0
        return hits / len(tokens)


class AnthropicRegistry:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def list_all(self) -> list[SkillInfo]:
        if not self._api_key:
            return []
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "anthropic-beta": _SKILLS_BETA,
        }
        results: list[SkillInfo] = []
        next_page: str | None = None
        try:
            async with httpx.AsyncClient(
                base_url=_ANTHROPIC_API_BASE, timeout=_HTTP_TIMEOUT
            ) as client:
                while True:
                    params: dict[str, Any] = {"limit": 100}
                    if next_page:
                        params["page"] = next_page
                    resp = await client.get(
                        "/v1/skills", headers=headers, params=params
                    )
                    resp.raise_for_status()
                    body = resp.json()
                    for skill in body.get("data", []):
                        info = await self._enrich(client, headers, skill)
                        results.append(info)
                    if not body.get("has_more"):
                        break
                    next_page = body.get("next_page")
                    if not next_page:
                        break
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Anthropic Skills API returned %s: %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
        except httpx.HTTPError as exc:
            logger.warning("Anthropic Skills API request failed: %s", exc)
        return results

    async def _enrich(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        skill: dict[str, Any],
    ) -> SkillInfo:
        skill_id = skill["id"]
        name = skill.get("display_title") or skill_id
        description = ""
        version = skill.get("latest_version", "")
        if version:
            try:
                resp = await client.get(
                    f"/v1/skills/{skill_id}/versions/{version}",
                    headers=headers,
                )
                resp.raise_for_status()
                vdata = resp.json()
                description = vdata.get("description", "")
                name = vdata.get("name") or name
            except httpx.HTTPError:
                pass
        return SkillInfo(
            id=skill_id,
            name=name,
            description=description,
            source=skill.get("source", "anthropic"),
            version=version,
        )

    async def search(self, query: str) -> list[SkillInfo]:
        all_skills = await self.list_all()
        scored = [(s, s.matches(query)) for s in all_skills]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [s for s, score in scored if score > 0]


class HttpRegistry:
    def __init__(self, url: str) -> None:
        self._url = url

    async def list_all(self) -> list[SkillInfo]:
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.get(self._url)
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("HTTP registry fetch failed for %s: %s", self._url, exc)
            return []
        except ValueError:
            logger.warning("HTTP registry returned invalid JSON: %s", self._url)
            return []

        results: list[SkillInfo] = []
        for entry in body.get("skills", []):
            results.append(
                SkillInfo(
                    id=entry.get("id", ""),
                    name=entry.get("name", ""),
                    description=entry.get("description", ""),
                    source="http",
                    download_url=entry.get("download_url", ""),
                    version=entry.get("version", ""),
                    tags=entry.get("tags", []),
                )
            )
        return results

    async def search(self, query: str) -> list[SkillInfo]:
        all_skills = await self.list_all()
        scored = [(s, s.matches(query)) for s in all_skills]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [s for s, score in scored if score > 0]


class SkillRegistryAggregator:
    def __init__(
        self,
        api_key: str = "",
        registry_urls: list[str] | None = None,
    ) -> None:
        self._anthropic = AnthropicRegistry(api_key)
        self._http_registries = [HttpRegistry(u) for u in (registry_urls or [])]

    async def search(self, query: str) -> list[SkillInfo]:
        results: list[SkillInfo] = []
        results.extend(await self._anthropic.search(query))
        for reg in self._http_registries:
            results.extend(await reg.search(query))
        seen: set[str] = set()
        deduped: list[SkillInfo] = []
        for skill in results:
            key = f"{skill.source}:{skill.id}"
            if key not in seen:
                seen.add(key)
                deduped.append(skill)
        return deduped

    async def list_all(self) -> list[SkillInfo]:
        results: list[SkillInfo] = []
        results.extend(await self._anthropic.list_all())
        for reg in self._http_registries:
            results.extend(await reg.list_all())
        return results
