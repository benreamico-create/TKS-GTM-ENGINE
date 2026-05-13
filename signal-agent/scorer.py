import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY
from models import StudentSignal

log = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SCORE_PROMPT = """\
You are evaluating whether a student is a strong fit for TKS (The Knowledge Society) \
— a program for ambitious students aged 13-17 who want to work on world-changing problems.

Score this profile 0.0–10.0 on likelihood they are an excellent TKS candidate.

High scores (8–10): Active builders, hackathon winners/finalists, FIRST Robotics \
top teams, GitHub repos with real technical depth, clear drive to solve hard problems.
Mid scores (4–7): Promising but unclear depth or age range.
Low scores (0–3): Casual hobbyists, likely outside age range, tutorial-level projects.

Return ONLY valid JSON: {"score": 7.5, "reason": "one sentence max 15 words"}

Profile:
{profile}"""


def score_signal(signal: StudentSignal) -> tuple[float, str]:
    if not ANTHROPIC_API_KEY:
        return 5.0, "no API key"

    profile = "\n".join(filter(None, [
        f"Source: {signal.source}",
        f"Name: {signal.name}",
        f"Competition: {signal.competition}" if signal.competition else None,
        f"Project: {signal.project_name}" if signal.project_name else None,
        f"Description: {signal.project_description}" if signal.project_description else None,
        f"School: {signal.school}" if signal.school else None,
        f"GitHub: {signal.github_url}" if signal.github_url else None,
        f"Location: {signal.location}" if signal.location else None,
    ]))

    try:
        response = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{"role": "user", "content": SCORE_PROMPT.format(profile=profile)}],
        )
        result = json.loads(response.content[0].text.strip())
        return float(result["score"]), result.get("reason", "")
    except Exception as e:
        log.warning(f"Scoring failed for {signal.name}: {e}")
        return 5.0, "scoring error"
