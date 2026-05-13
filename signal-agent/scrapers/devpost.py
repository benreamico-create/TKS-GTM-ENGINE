import logging
from typing import AsyncGenerator

import httpx

from models import StudentSignal

log = logging.getLogger(__name__)

DEVPOST_BASE = "https://devpost.com"
_HEADERS = {"User-Agent": "TKS-GTM-Signal-Agent/1.0"}


async def scrape_devpost() -> AsyncGenerator[StudentSignal, None]:
    async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
        resp = await client.get(
            f"{DEVPOST_BASE}/api/hackathons.json",
            params={"status": "open", "order_by": "recently-added", "per_page": "20"},
        )
        resp.raise_for_status()
        hackathons = resp.json().get("hackathons", [])

        for hackathon in hackathons[:5]:
            slug = hackathon.get("url", "").rstrip("/").split("/")[-1]
            if not slug:
                continue
            async for signal in _scrape_submissions(client, hackathon, slug):
                yield signal


async def _scrape_submissions(
    client: httpx.AsyncClient,
    hackathon: dict,
    slug: str,
) -> AsyncGenerator[StudentSignal, None]:
    try:
        resp = await client.get(
            f"https://{slug}.devpost.com/project-gallery.json",
            params={"page": "1", "per_page": "20"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.warning(f"Devpost submissions fetch failed ({slug}): {e}")
        return

    projects = data.get("software") or data.get("projects") or []

    for project in projects:
        for member in project.get("team_members") or []:
            username = member.get("username") or member.get("login", "")
            if not username:
                continue
            yield StudentSignal(
                source="devpost",
                external_id=f"{slug}:{username}",
                name=member.get("name") or username,
                github_url=f"https://github.com/{username}",
                project_name=project.get("title") or project.get("name"),
                project_url=project.get("url"),
                project_description=(project.get("description") or "")[:500],
                competition=hackathon.get("title") or hackathon.get("name"),
                raw_data={
                    "hackathon": hackathon.get("title"),
                    "project": project.get("title"),
                    "slug": slug,
                },
            )
