import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SCORE_PROMPT = """\
You are evaluating whether someone is a strong fit for TKS (The Knowledge Society) — \
a 10-month program exclusively for students aged 13–17 who want to work on hard problems \
in AI, biotech, climate, and other frontier areas.

CRITICAL: If the profile shows any sign this person is an adult professional (job title, \
company role, PhD, many years of experience, large following), score them 0–2 immediately. \
TKS only accepts students aged 13–17.

Score 0.0–10.0:
High (8–10): Clearly a teen, actively building real projects, hackathon winner/finalist, \
strong GitHub, driven by curiosity and impact.
Mid (5–7): Likely a student, shows promise but limited public work or unclear depth.
Low (3–4): Possibly a student but very little signal.
Very low (0–2): Adult professional, or clearly outside the 13–17 age range.

Return ONLY raw JSON, no markdown: {{"score": 7.5, "reason": "one sentence, max 15 words"}}

Profile:
{profile}"""


DRAFT_PROMPT = """\
You are a recruiter for TKS (The Knowledge Society), a 10-month program for students \
aged 13–17 who want to work on the world's most important problems. Alumni have gone on \
to publish research, launch startups, and work at top tech companies — as teenagers.

Write a short, warm, human outreach email to the student below. The email should:
- Open by referencing their SPECIFIC project or work (not generic praise)
- Be 3–4 sentences max — do not ramble
- Sound like a curious human who genuinely found their work, not a mass emailer
- Mention TKS in one sentence naturally
- End with a low-pressure question (not a hard sell)
- No subject line, no sign-off — just the email body

Student profile:
Name: {name}
Source: {source}
Project: {project_name}
Description: {project_description}
Competition/Context: {competition}
Location: {location}
GitHub: {github_url}
Score reason: {score_reason}"""


def score_signal(signal: dict) -> tuple[float, str]:
    if not ANTHROPIC_API_KEY:
        return 5.0, "no API key configured"

    profile = "\n".join(filter(None, [
        f"Name: {signal.get('name')}",
        f"Source: {signal.get('source')}",
        f"Location: {signal.get('location')}" if signal.get("location") else None,
        f"Project: {signal.get('project_name')}" if signal.get("project_name") else None,
        f"Description: {signal.get('project_description')}" if signal.get("project_description") else None,
        f"Competition: {signal.get('competition')}" if signal.get("competition") else None,
        f"GitHub: {signal.get('github_url')}" if signal.get("github_url") else None,
        f"Bio: {signal.get('raw_data', {}).get('bio')}" if signal.get("raw_data", {}).get("bio") else None,
        f"Public repos: {signal.get('raw_data', {}).get('public_repos')}" if signal.get("raw_data", {}).get("public_repos") else None,
        f"Top repo language: {signal.get('raw_data', {}).get('top_repo_language')}" if signal.get("raw_data", {}).get("top_repo_language") else None,
    ]))

    try:
        resp = _get_client().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{"role": "user", "content": SCORE_PROMPT.format(profile=profile)}],
        )
        text = resp.content[0].text.strip()
        # Strip markdown code fences if Claude wraps the JSON
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        return float(result["score"]), result.get("reason", "")
    except Exception as e:
        log.warning(f"Scoring failed for {signal.get('name')}: {e}")
        return 5.0, "scoring error"


def draft_email(signal: dict) -> str:
    if not ANTHROPIC_API_KEY:
        return "Add your ANTHROPIC_API_KEY to generate personalized emails."

    try:
        resp = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": DRAFT_PROMPT.format(
                    name=signal.get("name", ""),
                    source=signal.get("source", ""),
                    project_name=signal.get("project_name") or "their work",
                    project_description=signal.get("project_description") or "N/A",
                    competition=signal.get("competition") or "N/A",
                    location=signal.get("location") or "N/A",
                    github_url=signal.get("github_url") or "N/A",
                    score_reason=signal.get("score_reason") or "N/A",
                ),
            }],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        log.warning(f"Email draft failed for {signal.get('name')}: {e}")
        return "Could not generate email draft. Check your API key."
