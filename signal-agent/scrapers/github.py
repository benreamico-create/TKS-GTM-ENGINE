import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator

import httpx

from config import GITHUB_TOKEN
from models import StudentSignal

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


async def scrape_github() -> AsyncGenerator[StudentSignal, None]:
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    repo_queries = [
        f"hackathon student created:>{cutoff}",
        f"high-school programming created:>{cutoff} stars:>3",
        f"teen developer project created:>{cutoff}",
    ]

    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=30, headers=_headers()) as client:
        for query in repo_queries:
            try:
                resp = await client.get(
                    f"{GITHUB_API}/search/repositories",
                    params={"q": query, "sort": "updated", "order": "desc", "per_page": "20"},
                )
                resp.raise_for_status()
            except Exception as e:
                log.warning(f"GitHub repo search failed ({query!r}): {e}")
                continue

            for repo in resp.json().get("items", []):
                owner = repo.get("owner", {})
                username = owner.get("login", "")
                if not username or username in seen:
                    continue
                seen.add(username)

                yield StudentSignal(
                    source="github",
                    external_id=username,
                    name=username,
                    github_url=f"https://github.com/{username}",
                    project_name=repo.get("name"),
                    project_url=repo.get("html_url"),
                    project_description=(repo.get("description") or "")[:500],
                    competition="GitHub — trending student repos",
                    raw_data={
                        "repo": repo.get("full_name"),
                        "stars": repo.get("stargazers_count"),
                        "language": repo.get("language"),
                        "topics": repo.get("topics", []),
                    },
                )

        # Also surface users with student bios directly
        user_queries = [
            "high school student developer",
            "teen programmer robotics",
        ]
        for query in user_queries:
            try:
                resp = await client.get(
                    f"{GITHUB_API}/search/users",
                    params={"q": query, "sort": "repositories", "order": "desc", "per_page": "15"},
                )
                resp.raise_for_status()
            except Exception as e:
                log.warning(f"GitHub user search failed ({query!r}): {e}")
                continue

            for user in resp.json().get("items", []):
                username = user.get("login", "")
                if not username or username in seen:
                    continue
                seen.add(username)

                yield StudentSignal(
                    source="github",
                    external_id=username,
                    name=username,
                    github_url=user.get("html_url"),
                    competition="GitHub — student user search",
                    raw_data={"user_type": user.get("type"), "score": user.get("score")},
                )
