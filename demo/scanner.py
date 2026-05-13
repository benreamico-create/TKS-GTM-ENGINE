import asyncio
import hashlib
import logging

import httpx

from config import GITHUB_TOKEN, TARGET_CITIES

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEVPOST_BASE = "https://devpost.com"


def _gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _signal_id(source: str, external_id: str) -> str:
    return hashlib.sha256(f"{source}:{external_id}".encode()).hexdigest()[:16]


async def scan_github(client: httpx.AsyncClient) -> list[dict]:
    signals = []
    seen: set[str] = set()

    # Search by city for student/teen developers
    for city in TARGET_CITIES[:6]:  # limit to avoid rate limits in demo
        queries = [
            f"location:{city} followers:>10 repos:>3",
            f"location:{city} hackathon",
        ]
        for query in queries:
            try:
                resp = await client.get(
                    f"{GITHUB_API}/search/users",
                    params={"q": query, "sort": "repositories", "per_page": "8"},
                    headers=_gh_headers(),
                    timeout=20,
                )
                resp.raise_for_status()
                await asyncio.sleep(0.5)  # respect rate limit
            except Exception as e:
                log.warning(f"GitHub user search failed ({city}): {e}")
                continue

            for user in resp.json().get("items", []):
                username = user.get("login", "")
                if not username or username in seen:
                    continue
                seen.add(username)

                # Fetch profile for bio + location
                profile = await _fetch_github_profile(client, username)
                if not profile:
                    continue

                # Try to find their top repo
                top_repo = await _fetch_top_repo(client, username)

                signals.append({
                    "id": _signal_id("github", username),
                    "source": "github",
                    "name": profile.get("name") or username,
                    "github_url": f"https://github.com/{username}",
                    "project_name": top_repo.get("name") if top_repo else None,
                    "project_url": top_repo.get("html_url") if top_repo else None,
                    "project_description": (
                        top_repo.get("description") or ""
                    )[:400] if top_repo else None,
                    "competition": "GitHub",
                    "location": profile.get("location") or city,
                    "relevance_score": None,
                    "score_reason": None,
                    "raw_data": {
                        "username": username,
                        "bio": profile.get("bio"),
                        "public_repos": profile.get("public_repos"),
                        "followers": profile.get("followers"),
                        "top_repo_language": top_repo.get("language") if top_repo else None,
                        "top_repo_stars": top_repo.get("stargazers_count") if top_repo else None,
                    },
                })

    return signals


async def _fetch_github_profile(client: httpx.AsyncClient, username: str) -> dict | None:
    try:
        resp = await client.get(
            f"{GITHUB_API}/users/{username}",
            headers=_gh_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


async def _fetch_top_repo(client: httpx.AsyncClient, username: str) -> dict | None:
    try:
        resp = await client.get(
            f"{GITHUB_API}/users/{username}/repos",
            params={"sort": "stars", "per_page": "1"},
            headers=_gh_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        repos = resp.json()
        return repos[0] if repos else None
    except Exception:
        return None


async def scan_devpost(client: httpx.AsyncClient) -> list[dict]:
    signals = []
    headers = {"User-Agent": "TKS-GTM-Signal-Agent/1.0"}

    try:
        resp = await client.get(
            f"{DEVPOST_BASE}/api/hackathons.json",
            params={"status": "ended", "order_by": "recently-added", "per_page": "10"},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        hackathons = resp.json().get("hackathons", [])
    except Exception as e:
        log.warning(f"Devpost hackathon list failed: {e}")
        return signals

    for hackathon in hackathons[:4]:
        slug = hackathon.get("url", "").rstrip("/").split("/")[-1]
        if not slug:
            continue
        try:
            resp = await client.get(
                f"https://{slug}.devpost.com/project-gallery.json",
                params={"page": "1", "per_page": "15"},
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            projects = resp.json().get("software") or resp.json().get("projects") or []
        except Exception as e:
            log.debug(f"Devpost gallery failed ({slug}): {e}")
            continue

        for project in projects[:5]:
            for member in (project.get("team_members") or [])[:2]:
                username = member.get("username") or member.get("login", "")
                if not username:
                    continue
                signals.append({
                    "id": _signal_id("devpost", f"{slug}:{username}"),
                    "source": "devpost",
                    "name": member.get("name") or username,
                    "github_url": f"https://github.com/{username}",
                    "project_name": project.get("title") or project.get("name"),
                    "project_url": project.get("url"),
                    "project_description": (project.get("description") or "")[:400],
                    "competition": hackathon.get("title") or hackathon.get("name"),
                    "location": None,
                    "relevance_score": None,
                    "score_reason": None,
                    "raw_data": {
                        "hackathon": hackathon.get("title"),
                        "slug": slug,
                        "username": username,
                    },
                })

    return signals


async def run_scan() -> list[dict]:
    async with httpx.AsyncClient() as client:
        github_signals, devpost_signals = await asyncio.gather(
            scan_github(client),
            scan_devpost(client),
            return_exceptions=True,
        )

    results = []
    if isinstance(github_signals, list):
        results.extend(github_signals)
    if isinstance(devpost_signals, list):
        results.extend(devpost_signals)

    log.info(f"Scan complete — {len(results)} raw signals found")
    return results
