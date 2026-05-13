import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import DB_PATH, MIN_SCORE_THRESHOLD
from drafter import draft_email, score_signal
from scanner import run_scan
from store import SignalStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="TKS Signal Engine")
store = SignalStore(DB_PATH)

app.mount("/static", StaticFiles(directory="static"), name="static")

_scan_running = False


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return Path("static/index.html").read_text()


@app.get("/api/signals")
async def get_signals():
    signals = store.get_all()
    return {
        "signals": signals,
        "total": len(signals),
        "high_quality": sum(1 for s in signals if (s.get("relevance_score") or 0) >= MIN_SCORE_THRESHOLD),
    }


@app.post("/api/scan")
async def trigger_scan():
    global _scan_running
    if _scan_running:
        return {"status": "already_running", "message": "Scan already in progress"}

    asyncio.create_task(_run_scan_task())
    return {"status": "started", "message": "Scan started — refresh signals in ~30 seconds"}


@app.get("/api/scan/status")
async def scan_status():
    return {"running": _scan_running}


@app.post("/api/signals/{signal_id}/draft")
async def generate_draft(signal_id: str):
    signal = store.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    if signal.get("email_draft"):
        return {"draft": signal["email_draft"], "cached": True}

    draft = draft_email(signal)
    store.save_email_draft(signal_id, draft)
    return {"draft": draft, "cached": False}


async def _run_scan_task():
    global _scan_running
    _scan_running = True
    try:
        raw_signals = await run_scan()
        new_count = 0
        for signal in raw_signals:
            if store.exists(signal["id"]):
                continue
            score, reason = score_signal(signal)
            signal["relevance_score"] = score
            signal["score_reason"] = reason
            if store.save(signal):
                new_count += 1
                log.info(f"NEW [{signal['source']}] {signal['name']} | score={score:.1f} | {reason}")
        log.info(f"Scan done — {new_count} new signals added (total: {store.count()})")
    except Exception as e:
        log.error(f"Scan failed: {e}", exc_info=True)
    finally:
        _scan_running = False
