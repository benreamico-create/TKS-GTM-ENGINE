import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
FIRST_API_KEY = os.environ.get("FIRST_API_KEY", "")
FIRST_API_SECRET = os.environ.get("FIRST_API_SECRET", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))
DB_PATH = os.environ.get("DB_PATH", "data/signals.db")
SIGNALS_QUEUE_PATH = os.environ.get("SIGNALS_QUEUE_PATH", "data/queue.jsonl")
MIN_SCORE_THRESHOLD = float(os.environ.get("MIN_SCORE_THRESHOLD", "6.0"))
