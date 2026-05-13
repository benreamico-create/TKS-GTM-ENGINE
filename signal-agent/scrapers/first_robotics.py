import base64
import logging
from datetime import datetime
from typing import AsyncGenerator

import httpx

from config import FIRST_API_KEY, FIRST_API_SECRET
from models import StudentSignal

log = logging.getLogger(__name__)

FIRST_API = "https://frc-api.firstinspires.org/v3.0"
SEASON = datetime.utcnow().year


def _auth_headers() -> dict | None:
    if not FIRST_API_KEY or not FIRST_API_SECRET:
        return None
    token = base64.b64encode(f"{FIRST_API_KEY}:{FIRST_API_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def scrape_first_robotics() -> AsyncGenerator[StudentSignal, None]:
    headers = _auth_headers()
    if not headers:
        log.info("FIRST Robotics: no credentials configured, skipping")
        return

    async with httpx.AsyncClient(timeout=30, headers=headers) as client:
        try:
            resp = await client.get(f"{FIRST_API}/{SEASON}/events")
            resp.raise_for_status()
            events = resp.json().get("Events", [])
        except Exception as e:
            log.warning(f"FIRST events fetch failed: {e}")
            return

        for event in events[:10]:
            event_code = event.get("code", "")
            if not event_code:
                continue

            try:
                resp = await client.get(f"{FIRST_API}/{SEASON}/rankings/{event_code}")
                resp.raise_for_status()
                rankings = resp.json().get("Rankings", [])
            except Exception as e:
                log.debug(f"FIRST rankings fetch failed ({event_code}): {e}")
                continue

            # Top 5 teams per event — these are the kids we want
            for entry in rankings[:5]:
                team_number = entry.get("teamNumber")
                if not team_number:
                    continue

                yield StudentSignal(
                    source="first_robotics",
                    external_id=f"{event_code}:{team_number}",
                    name=f"FRC Team {team_number}",
                    competition=f"FIRST Robotics — {event.get('name', event_code)}",
                    location=(
                        f"{event.get('city', '')}, {event.get('stateprov', '')}".strip(", ")
                        or None
                    ),
                    raw_data={
                        "team_number": team_number,
                        "event_code": event_code,
                        "rank": entry.get("rank"),
                        "wins": entry.get("wins"),
                        "losses": entry.get("losses"),
                    },
                )
