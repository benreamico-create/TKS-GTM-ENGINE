import logging
from typing import AsyncGenerator

import httpx
from bs4 import BeautifulSoup

from models import StudentSignal

log = logging.getLogger(__name__)

MLH_EVENTS_URL = "https://mlh.io/seasons/2025/events"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TKS-Signal-Agent/1.0)"}


async def scrape_mlh() -> AsyncGenerator[StudentSignal, None]:
    """
    Scrapes MLH event listings. MLH events link to Devpost hackathons;
    the Devpost scraper handles participant data. This scraper feeds
    event metadata so we can cross-reference competition signals.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=_HEADERS) as client:
        try:
            resp = await client.get(MLH_EVENTS_URL)
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"MLH events fetch failed: {e}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        # MLH uses different selectors across seasons; try broadly
        events = soup.select(".event-wrapper, .event-block, [class*='event-name']")

        log.info(f"MLH: found {len(events)} event elements")

        for event in events[:20]:
            name_el = event.select_one("h3, h4, .event-name, strong")
            link_el = event.find_parent("a") or event.select_one("a[href]")

            if not name_el:
                continue

            event_name = name_el.get_text(strip=True)
            event_url = link_el.get("href", "") if link_el else ""

            # Only surface if it links to a Devpost hackathon we haven't seen
            if "devpost.com" in event_url:
                slug = event_url.rstrip("/").split("/")[-1]
                yield StudentSignal(
                    source="mlh",
                    external_id=slug,
                    name=f"MLH Event: {event_name}",
                    competition=event_name,
                    project_url=event_url,
                    raw_data={"event_name": event_name, "url": event_url},
                )
