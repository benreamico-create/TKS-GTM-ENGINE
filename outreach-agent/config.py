import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")

SIGNALS_QUEUE_PATH = os.environ.get("SIGNALS_QUEUE_PATH", "data/queue.jsonl")
DB_PATH = os.environ.get("DB_PATH", "data/outreach.db")

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "60"))

# TKS recruiter name shown in outreach emails
SENDER_NAME = os.environ.get("SENDER_NAME", "TKS Team")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "hello@tks.world")

# HubSpot lifecycle stage for newly created contacts
# Values: subscriber, lead, marketingqualifiedlead, salesqualifiedlead, opportunity, customer, evangelist, other
HUBSPOT_LIFECYCLE_STAGE = os.environ.get("HUBSPOT_LIFECYCLE_STAGE", "lead")

# HubSpot owner ID to assign contacts to (optional)
HUBSPOT_OWNER_ID = os.environ.get("HUBSPOT_OWNER_ID", "")
