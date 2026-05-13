import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

DB_PATH = os.environ.get("DB_PATH", "data/signals.db")

# Tech cities in Canada + US to target
TARGET_CITIES = [
    "Toronto", "Vancouver", "Montreal",
    "San Francisco", "Seattle", "New York",
    "Boston", "Austin", "Los Angeles", "Chicago",
]

MIN_SCORE_THRESHOLD = float(os.environ.get("MIN_SCORE_THRESHOLD", "6.0"))
