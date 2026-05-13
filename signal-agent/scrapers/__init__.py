import logging
from typing import AsyncGenerator

from models import StudentSignal
from scrapers.devpost import scrape_devpost
from scrapers.first_robotics import scrape_first_robotics
from scrapers.github import scrape_github
from scrapers.hackathons import scrape_mlh

log = logging.getLogger(__name__)

_SCRAPERS = [
    ("Devpost", scrape_devpost),
    ("GitHub", scrape_github),
    ("FIRST Robotics", scrape_first_robotics),
    ("MLH", scrape_mlh),
]


async def run_all_scrapers() -> AsyncGenerator[StudentSignal, None]:
    for name, scraper in _SCRAPERS:
        try:
            async for signal in scraper():
                yield signal
        except Exception as e:
            # Self-healing: one broken scraper never stops the others
            log.error(f"{name} scraper failed: {e}", exc_info=True)
