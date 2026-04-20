"""
Three content generators, one per daily post slot:

  generate_news_digest(research)         → 10 AM BD  — 3 top tech/AI news items (English)
  generate_tutorial_bengali(posted)      → 8 PM BD   — Bengali lesson with visual config
  generate_motivational_quote()          → 11 PM BD  — Short motivational quote for image
"""

import json
import re
import anthropic
from config import ANTHROPIC_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── shared helpers ────────────────────────────────────────────────────────────

def _call(system: str, user: str, max_tokens: int = 1500) -> str:
    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw.strip())


# ── slot 1: tech news digest (10 AM BD) ──────────────────────────────────────

_NEWS_SYSTEM = """\
You are a tech journalist writing for a Facebook page that covers technology, AI, and the digital world.
Write engaging, reader-friendly posts. Use emojis naturally. Always return valid JSON only — no markdown, no commentary.
"""

_NEWS_PROMPT = """\
Based on the research below, write a Facebook post covering the 3 most important or hyped technology/AI updates of last 24 hours.

Research:
{research}

Format each update with:
- A bold headline using emoji. emoji should be professional
- 2–3 sentence summary in plain English
- Why it matters in 1 sentence

End with 4–5 relevant hashtags.

Return ONLY this JSON:
{{"post_text": "<full formatted FB post>"}}
"""


def generate_news_digest(research: str) -> dict:
    logger.info("Generating tech news digest...")
    raw = _call(_NEWS_SYSTEM, _NEWS_PROMPT.format(research=research))
    result = _parse_json(raw)
    logger.info("News digest generated.")
    return result


# ── slot 2: Bengali tutorial (8 PM BD) ───────────────────────────────────────

_TUTORIAL_SYSTEM = """\
You are an expert Bengali-speaking educator in data science, machine learning, statistics, AI, databases, and data engineering.
You write clear, beginner-friendly lessons in Bengali for Facebook.
- Use simple, everyday Bengali words — avoid overly formal language
- Use relatable Bangladeshi examples where possible
- Keep post text 300–500 words in Bengali
- Visual labels/data must be in English (for chart/diagram rendering)
Return valid JSON only — no markdown, no extra text.
"""

_TUTORIAL_PROMPT = """\
Already-covered topics (DO NOT repeat any of these):
{posted}

Pick ONE fresh, specific topic from these domains:
Statistics, Data Science, Data Analytics, Data Engineering, Machine Learning, AI/LLMs,
Data Warehousing, Database Design, SQL, Python for Data, Probability, Feature Engineering,
Model Evaluation, Deep Learning, NLP, Computer Vision, Cloud Data Services, ETL pipelines.

Write a beginner-friendly Bengali tutorial post for this topic.

Then choose the visual that BEST serves this specific topic's pedagogy — not a generic chart.
Think: what would a great textbook or YouTube thumbnail use to explain THIS concept visually?

Available visual types and when to use them:

  "chart" with chart_type "bar"       — comparisons, rankings, category counts
  "chart" with chart_type "line"      — trends over time, learning curves, epochs
  "chart" with chart_type "pie"       — proportions, distributions, market share
  "chart" with chart_type "scatter"   — correlation, clustering, regression visualization
  "chart" with chart_type "histogram" — frequency distribution, data spread
  "flowchart"                         — algorithms, decision logic, pipelines, step-by-step processes

Rules for visual_config:
- All text (labels, titles, axis names) must be in English
- Use REAL, meaningful data/values that actually illustrate the concept
  (not placeholder 10/20/30 — use numbers that tell a story)
- For scatter: provide "x_values" and "y_values" as lists
- For histogram: provide "data" as a flat list of raw values
- For flowchart: write clean, valid Mermaid.js syntax

Return ONLY valid JSON in one of these shapes:

Chart:
{{"topic_en": "...", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "bar|line|pie|scatter|histogram", "labels": [...], "values": [...], "xlabel": "...", "ylabel": "..."}}}}

Scatter:
{{"topic_en": "...", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "scatter", "x_values": [...], "y_values": [...], "xlabel": "...", "ylabel": "..."}}}}

Histogram:
{{"topic_en": "...", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "histogram", "data": [...], "xlabel": "...", "ylabel": "Frequency"}}}}

Flowchart:
{{"topic_en": "...", "post_text": "...Bengali...", "visual_type": "flowchart", "visual_config": {{"title": "...", "mermaid_code": "graph TD\\n  ..."}}}}
"""


def generate_tutorial_bengali(posted_topics: list[str]) -> dict:
    logger.info("Generating Bengali tutorial post...")
    posted_str = "\n".join(f"- {t}" for t in posted_topics) if posted_topics else "(none yet)"
    raw = _call(_TUTORIAL_SYSTEM, _TUTORIAL_PROMPT.format(posted=posted_str), max_tokens=2500)
    result = _parse_json(raw)
    logger.info(f"Tutorial generated — topic: {result.get('topic_en')}")
    return result


# ── slot 3: motivational quote (11 PM BD) ─────────────────────────────────────

_QUOTE_SYSTEM = """\
You write powerful, original motivational quotes for a professional Facebook page.
Style: short punchy statements, similar to Jeff Moore / stoic quote pages.
Themes: career growth, skill-building, money mindset, consistency, resilience, life wisdom.
The quote will be rendered as bold white text on a pure black background image.
Return valid JSON only — no markdown, no commentary.
"""

_QUOTE_PROMPT = """\
Write an original motivational quote in the style of the examples below.
The quote should feel authentic — NOT clichéd or generic.

Style examples:
Example 1:
  "There's a future version of you
  sitting around telling a story about
  how you went through failure, setbacks,
  and rejection and still came out on top.

  Keep going."

Example 2:
  "If you're determined, you'll get it.

  If you're disciplined, you'll grow it.

  If you're grateful, you'll attract more of it.

  Keep going."

Rules:
- 2–4 short paragraphs (each paragraph = 1–3 short lines)
- Last paragraph is a short punchy closer (like "Keep going." or "That's the work.")
- Theme: career, money, skill, resilience, or life wisdom
- Each paragraph should be short enough to fit ~30 chars wide on screen

Return ONLY this JSON:
{{
  "quote_paragraphs": ["paragraph 1 text", "paragraph 2 text", "closing line"],
  "fb_caption": "Full quote as a single text block for FB post caption"
}}
"""


def generate_motivational_quote() -> dict:
    logger.info("Generating motivational quote...")
    raw = _call(_QUOTE_SYSTEM, _QUOTE_PROMPT)
    result = _parse_json(raw)
    logger.info("Quote generated.")
    return result
