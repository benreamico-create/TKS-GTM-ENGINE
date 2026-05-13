import asyncio
import json
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import MIN_SCORE_THRESHOLD, POLL_INTERVAL_SECONDS, SIGNALS_QUEUE_PATH, DB_PATH
from models import StudentSignal
from scorer import score_signal
from scrapers import run_all_scrapers
from store import SignalStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("signal-agent")

store = SignalStore(DB_PATH)


async def poll():
    log.info("Poll started")
    new_count = 0

    async for signal in run_all_scrapers():
        if store.is_seen(signal.source, signal.external_id):
            continue

        try:
            score, reason = score_signal(signal)
            signal.relevance_score = score
            signal.score_reason = reason
        except Exception as e:
            log.warning(f"Scorer error for {signal.name}: {e}")

        if not store.save(signal):
            continue  # race condition — another coroutine saved it first

        new_count += 1
        log.info(
            f"NEW [{signal.source}] {signal.name} | "
            f"score={signal.relevance_score:.1f} | {signal.score_reason} | "
            f"{signal.competition or 'no competition'}"
        )

        # Only push high-quality signals to the outreach queue
        if (signal.relevance_score or 0) >= MIN_SCORE_THRESHOLD:
            _enqueue(signal)

    log.info(f"Poll complete — {new_count} new signals (total in DB: {store.count()})")


def _enqueue(signal: StudentSignal):
    path = Path(SIGNALS_QUEUE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(signal.model_dump(mode="json")) + "\n")


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(poll()),
        "interval",
        seconds=POLL_INTERVAL_SECONDS,
        id="signal_poll",
        max_instances=1,  # never overlap runs
    )
    scheduler.start()
    log.info(f"Signal Agent live — polling every {POLL_INTERVAL_SECONDS}s")

    await poll()  # immediate run on startup

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
