"""
Three content generators, one per daily post slot:

  generate_news_digest(research)         → 10 AM BD  — 3 top tech/AI news items (Bengali)
  generate_tutorial_bengali(posted)      → 8 PM BD   — Bengali lesson with visual config
  generate_motivational_quote()          → 11 PM BD  — Short motivational quote for image
"""

import json
import re
from datetime import datetime
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


def _extract_json_block(raw: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1].strip()
    return cleaned.strip()


def _repair_json(raw: str) -> dict:
    """Ask the model to repair malformed JSON into a valid object."""
    repair_system = (
        "You repair malformed JSON. "
        "Return one valid JSON object only. "
        "Do not add markdown, comments, or explanation."
    )
    repair_prompt = f"""\
The following text was supposed to be a valid JSON object but is malformed.
Repair it into valid JSON while preserving the intended meaning.

Malformed text:
{raw}
"""
    repaired = _call(repair_system, repair_prompt, max_tokens=2500)
    repaired_block = _extract_json_block(repaired)
    return json.loads(repaired_block)


def _parse_json(raw: str) -> dict:
    json_block = _extract_json_block(raw)
    try:
        return json.loads(json_block)
    except json.JSONDecodeError as exc:
        logger.warning(f"Malformed JSON from model, attempting repair: {exc}")
        return _repair_json(json_block)


# ── slot 1: tech news digest (10 AM BD) ──────────────────────────────────────

_NEWS_SYSTEM = """\
You are a tech journalist writing for a Bangladeshi Facebook page covering technology, AI, and the digital world.
Write all post content in Bengali (বাংলা) — simple, everyday Bengali that general readers can understand.
The page voice is not a generic news bot. It is a Bangla-first tech explainer page with sharp but grounded takes.
The writing should feel original, timely, and specific to the day's stories.
Use emojis naturally. Always return valid JSON only — no markdown, no commentary.
"""

_NEWS_PROMPT = """\
Based on the research below, write a Facebook post IN BENGALI covering the 3 most important technology/AI updates of the last 24 hours.

Research:
{research}

Today's editorial style:
{style_block}

Today's post format:
{format_block}

This page should NOT sound like a repetitive roundup bot.
Avoid generic openings such as:
- "আজকের সেরা ৩টি AI আপডেট"
- "🤖 আজকের সেরা ৩টি AI আপডেট — একসাথে জেনে নিন!"
- "প্রযুক্তির দুনিয়া থেকে"
- any close variation of those lines

Instead, open with ONE fresh hook line that matches the day's actual news mood.
Rotate naturally across these hook styles:
- surprise / "আজকের AI দুনিয়ায় সবচেয়ে interesting ব্যাপার হলো..."
- consequence / "আজকের ৩টা আপডেট একসাথে দেখলে একটা trend পরিষ্কার..."
- career angle / "ডেটা আর AI নিয়ে কাজ করলে আজকের খবরগুলো আপনার জন্য important..."
- industry shift / "AI race আজকে আরেক ধাপ বদলে গেল..."
- debate angle / "আজকের খবর দেখে একটা প্রশ্ন আবার সামনে এলো..."

The opening hook must:
- be 1 short paragraph only
- feel specific and human, not slogan-like
- avoid sounding like a template
- avoid announcing "top 3 updates" in the first sentence

Format each update with:
- A bold Bengali headline with a professional emoji
- 2–3 sentence summary in simple Bengali
- Why it matters — 1 sentence in Bengali
- One short "আমাদের takeaway" style line explaining what data/AI people should notice or learn from this news
- Source link on its own line: 🔗 <URL>  (use the matching URL from the research)

Then end the whole post with:
- 1 short closing paragraph that connects the 3 stories into a bigger pattern or shift
- 1 natural comment-driving question in Bengali

End with 4–5 relevant hashtags (can be English hashtags).

Return ONLY this JSON:
{{"post_text": "<full formatted FB post in Bengali>", "headlines": ["short headline 1", "short headline 2", "short headline 3"]}}

headlines must be plain short English titles (max 6 words each, no emoji) — used for the cover image only.
"""


_NEWS_STYLES = [
    {
        "name": "Trend Spotter",
        "description": (
            "Open by identifying the biggest pattern connecting today's stories. "
            "Sound sharp, observant, and forward-looking."
        ),
    },
    {
        "name": "Why It Matters",
        "description": (
            "Lead with consequences. Focus on what changes for users, builders, teams, "
            "or the market because of these updates."
        ),
    },
    {
        "name": "Career Lens",
        "description": (
            "Frame the news through the lens of data, AI, analytics, and tech careers. "
            "Highlight what professionals should pay attention to or learn next."
        ),
    },
    {
        "name": "Big Shift",
        "description": (
            "Make the post feel like today's news marks a larger industry move. "
            "Connect separate updates into one broader transition."
        ),
    },
    {
        "name": "Debate Starter",
        "description": (
            "Use a hook that naturally invites discussion. The tone should feel thoughtful, "
            "not clickbait, and should surface a real tension in today's news."
        ),
    },
    {
        "name": "Explainer Mode",
        "description": (
            "Assume the audience is curious but busy. Explain the news clearly and simply, "
            "without sounding basic or repetitive."
        ),
    },
]

_NEWS_FORMATS = [
    {
        "name": "Equal Roundup",
        "description": (
            "Treat all 3 stories with roughly equal importance. "
            "Give each story similar space and energy."
        ),
    },
    {
        "name": "Lead Story + Quick Hits",
        "description": (
            "Make the biggest story clearly feel like the main event. "
            "Give it extra depth, then cover the other 2 as shorter quick hits."
        ),
    },
    {
        "name": "One Big Angle",
        "description": (
            "Frame all 3 updates under one shared theme or tension. "
            "The post should read like one coherent narrative, not 3 disconnected summaries."
        ),
    },
    {
        "name": "Career Briefing",
        "description": (
            "Prioritize what these 3 updates signal for people working in data, AI, analytics, "
            "engineering, or tech careers. Keep it practical."
        ),
    },
    {
        "name": "Market Watch",
        "description": (
            "Focus on company moves, product shifts, competition, and strategic implications. "
            "Make the post feel like a sharp industry briefing."
        ),
    },
]


def _news_style_for_today() -> dict:
    """Rotate news voice by day without storing history."""
    day_index = datetime.now().toordinal()
    return _NEWS_STYLES[day_index % len(_NEWS_STYLES)]


def _news_format_for_today() -> dict:
    """Rotate post structure by day without storing history."""
    day_index = datetime.now().toordinal()
    return _NEWS_FORMATS[(day_index * 3) % len(_NEWS_FORMATS)]


def generate_news_digest(research: str) -> dict:
    logger.info("Generating tech news digest...")
    style = _news_style_for_today()
    news_format = _news_format_for_today()
    style_block = (
        f"- Style name: {style['name']}\n"
        f"- Style guidance: {style['description']}\n"
        "- Follow this style strongly for the hook, transitions, and closing."
    )
    format_block = (
        f"- Format name: {news_format['name']}\n"
        f"- Format guidance: {news_format['description']}\n"
        "- Reflect this format in the balance, pacing, and transitions of the full post."
    )
    logger.info(f"News style selected: {style['name']}")
    logger.info(f"News format selected: {news_format['name']}")
    raw = _call(
        _NEWS_SYSTEM,
        _NEWS_PROMPT.format(
            research=research,
            style_block=style_block,
            format_block=format_block,
        ),
        max_tokens=2500,
    )
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


# ── viral content jobs (manual cron-friendly runners) ────────────────────────

_VIRAL_SYSTEM = """\
You create high-engagement Facebook content for a Bangla-first data/AI page.
The page voice is sharp, practical, opinionated, and easy to understand.
Avoid generic motivation and avoid sounding like a content farm.
Write in natural Bengali with occasional familiar English tech words when that feels more real.
Return valid JSON only.
"""

_VIRAL_PROMPT = """\
Create ONE viral-style Facebook post for the `{slot_name}` slot.

Slot intent:
{slot_guidance}

Assigned category for this run:
- Category: {category_name}
- Category guidance: {category_guidance}

Optional research/context:
{research}

Requirements:
- Pick ONE fresh, specific angle that fits the assigned category
- Make the post feel natural and not templated
- Use a strong hook in the first 1-2 lines
- The body should be concise but valuable
- Add 1 natural question or CTA at the end when it helps comments
- Keep it highly shareable/saveable

Visual requirements:
- Choose whether this post needs an illustration/image by setting visual_type to "viral"
- The image style should complement the idea using catchy cartoon-style, editorial illustration, or clean social graphic direction
- Write the image prompt in English for image generation
- Keep on-image text short

Return ONLY this JSON:
{{
  "category": "{category_name}",
  "topic_en": "short internal topic label",
  "post_text": "full Bengali Facebook post",
  "visual_type": "viral",
  "visual_config": {{
    "tag": "short category tag",
    "title": "short on-image title",
    "subtitle": "optional one-line support text",
    "bullets": ["short bullet 1", "short bullet 2", "short bullet 3"],
    "prompt": "English image prompt for a catchy cartoon/editorial illustration/social image"
  }}
}}

Rules for visual_config:
- title must be short, punchy, and in English
- bullets should be short English snippets if used
- prompt should describe a square social-media-friendly illustration with strong focal point
- avoid photorealistic celebrity faces or copyrighted characters
"""

_VIRAL_DAY_CATEGORIES = [
    {
        "name": "News Take",
        "guidance": "Use a current tech/AI development and add a sharp but grounded take on why it matters.",
    },
    {
        "name": "Hot Topic Explainer",
        "guidance": "Take one hot AI/data topic and explain it simply in a shareable way.",
    },
    {
        "name": "Debate Post",
        "guidance": "Create a real opinion or tension point that invites comments, not empty engagement bait.",
    },
]

_VIRAL_NIGHT_CATEGORIES = [
    {
        "name": "Career Lesson",
        "guidance": "Teach one honest lesson about building a stronger data/AI career with practical insight.",
    },
    {
        "name": "Mistake To Avoid",
        "guidance": "Highlight one common mistake people make in data learning, job prep, or AI work.",
    },
    {
        "name": "Checklist / Roadmap",
        "guidance": "Give a compact, useful checklist or roadmap people will want to save.",
    },
    {
        "name": "Mini Case Study",
        "guidance": "Use a simple business or product example to explain a data/AI concept in a practical way.",
    },
]


def _viral_slot_config(slot_name: str) -> tuple[str, list[dict]]:
    if slot_name == "day":
        return (
            "Day slot: prioritize current, discussion-friendly, shareable content tied to live trends or fresh talking points.",
            _VIRAL_DAY_CATEGORIES,
        )
    if slot_name == "night":
        return (
            "Night slot: prioritize reflective, save-worthy, practical content around skills, careers, mistakes, and real examples.",
            _VIRAL_NIGHT_CATEGORIES,
        )
    raise ValueError(f"Unknown viral slot: {slot_name}")


def _viral_category_for_today(slot_name: str) -> dict:
    slot_guidance, categories = _viral_slot_config(slot_name)
    del slot_guidance
    day_index = datetime.now().toordinal()
    step = 2 if slot_name == "day" else 3
    offset = 1 if slot_name == "day" else 2
    return categories[(day_index * step + offset) % len(categories)]


def generate_viral_content(slot_name: str, research: str = "") -> dict:
    logger.info(f"Generating viral content for {slot_name} slot...")
    slot_guidance, _ = _viral_slot_config(slot_name)
    category = _viral_category_for_today(slot_name)
    research_block = research if research else "(none provided - rely on general knowledge and originality)"
    raw = _call(
        _VIRAL_SYSTEM,
        _VIRAL_PROMPT.format(
            slot_name=slot_name,
            slot_guidance=slot_guidance,
            category_name=category["name"],
            category_guidance=category["guidance"],
            research=research_block,
        ),
        max_tokens=2200,
    )
    result = _parse_json(raw)
    logger.info(f"Viral content generated — slot={slot_name} | category={result.get('category')}")
    return result


# ── archived quote generator (disabled from active schedule) ──────────────────

_QUOTE_SYSTEM = """\
You write short, powerful career and money lessons for a data professional's Facebook page.
Voice: someone who has actually worked in data, seen the income gap, and built real skills.
The quotes feel personal — like advice from a mentor who has been through it.
Style: 2–3 tight lines of truth, then a closing line that feels like a direct message to the reader.
The quote will be rendered as bold white text on a pure black background image.
Return valid JSON only — no markdown, no commentary.
"""

_QUOTE_PROMPT = """\
Write an original career/money lesson in the style of the examples below.
It must feel like lived experience from someone who works in data — NOT generic advice.

Style examples:
Example 1:
  "Most people in data get paid for what they know.
  The top earners get paid for what they can change.

  Learn to show business impact. That's the gap."

Example 2:
  "I used to think more certifications meant more money.
  Then I learned to speak in revenue, not techniques.

  That one shift changed my salary conversation forever."

Example 3:
  "You're not underpaid because you lack skills.
  You're underpaid because nobody knows what your skills are worth.

  Start making that visible."

Rules:
- Exactly 2 paragraphs of 1–2 lines each (the main lesson)
- Then 1 short closing line that speaks directly to the reader ("That's the shift." / "I've seen it change everything." / "That's where the money is.")
- Focus: data career, salary negotiation, skill-to-income gap, building credibility, real lessons from data work
- Each line must fit ~32 chars wide on screen — keep lines SHORT
- Do NOT use "Keep going" — the closing must be specific to the lesson

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
