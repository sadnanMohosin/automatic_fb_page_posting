"""
Three content generators, one per daily post slot:

  generate_news_digest(research)         → 10 AM BD  — 3 top tech/AI news items (Bengali)
  plan_tutorial_bengali(history)         → 8 PM BD   — choose family/difficulty/topic for the tutorial
  generate_tutorial_bengali(...)         → 8 PM BD   — researched Bengali lesson with rich visual config
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
You are an expert Bengali-speaking educator for a Bangla-first Facebook page about data, AI, analytics, SQL, and engineering.
You do NOT write generic chapter summaries. You make complex topics feel learnable, practical, and save-worthy.
The audience is mixed:
- curious beginners
- job-seekers trying to grow into data roles
- intermediate practitioners who want sharper mental models

Writing rules:
- Use clear, conversational Bengali
- Use familiar English technical words when they sound natural
- Keep sections short and skimmable for Facebook
- Teach with one strong example, not a wall of theory
- Make the post feel helpful, not academic and not engagement bait
- Visual labels/data must be in English
Return valid JSON only — no markdown, no commentary.
"""

_TUTORIAL_PLAN_SYSTEM = """\
You are a curriculum strategist for a Bangla-first Facebook page about data careers and AI.
This page covers the full data ecosystem: data analytics, data science, machine learning, AI, data engineering,
data warehousing, BI, statistics, databases, experimentation, and applied systems.
Choose tutorial topics that feel sharper than textbook 101 topics.
Prefer practical concepts, failure modes, tradeoffs, debugging situations, architectural thinking, or decision-making skills.
Keep originality high: do not recycle a tiny fixed menu of topics.
Return one valid JSON object only.
"""

_TUTORIAL_DIFFICULTIES = {
    "foundation": {
        "label": "Foundation Refresh",
        "guidance": (
            "Pick a foundational concept with a practical twist. It still must feel specific and useful, "
            "not like a broad beginner chapter title."
        ),
    },
    "intermediate": {
        "label": "Intermediate Builder",
        "guidance": (
            "Pick a practical concept that real learners often misuse, misunderstand, or need in actual work."
        ),
    },
    "advanced": {
        "label": "Advanced But Explainable",
        "guidance": (
            "Pick a nuanced concept involving tradeoffs, failure modes, architecture, or evaluation. "
            "The topic can be advanced, but the explanation must stay simple."
        ),
    },
}

_TUTORIAL_DIFFICULTY_SCHEDULE = [
    "intermediate",
    "advanced",
    "intermediate",
    "advanced",
    "foundation",
    "intermediate",
    "advanced",
]

_TUTORIAL_FAMILIES = [
    {
        "id": "sql_analytics",
        "name": "SQL and Analytics Engineering",
        "focus": "SQL logic, query grain, window functions, joins, deduplication, cohort logic, aggregation mistakes, semantic layers",
        "examples": {
            "foundation": "COUNT(*) vs COUNT(column), NULL behavior, GROUP BY grain",
            "intermediate": "join duplication, window functions, cohort analysis, query debugging",
            "advanced": "sessionization, attribution windows, semantic modeling, advanced analytical SQL",
        },
    },
    {
        "id": "data_warehousing",
        "name": "Data Warehousing and Modeling",
        "focus": "star schema, fact vs dimension tables, warehouse design, cardinality, slowly changing dimensions, dimensional modeling",
        "examples": {
            "foundation": "fact table vs dimension table",
            "intermediate": "choosing the right grain, snapshot tables, warehouse design decisions",
            "advanced": "SCD Type 2 tradeoffs, bridge tables, semantic layer design",
        },
    },
    {
        "id": "data_science_ml",
        "name": "Data Science and Machine Learning",
        "focus": "model evaluation, validation strategy, leakage, feature design, class imbalance, model behavior, training pitfalls",
        "examples": {
            "foundation": "accuracy vs precision vs recall",
            "intermediate": "ROC vs PR, leakage, overfitting, validation mistakes",
            "advanced": "calibration, threshold tuning, offline vs online mismatch, feature-store consistency",
        },
    },
    {
        "id": "feature_engineering",
        "name": "Feature Engineering and Data Preparation",
        "focus": "feature design, leakage, encoding, temporal windows, aggregation logic, feature drift, training-serving mismatch",
        "examples": {
            "foundation": "categorical encoding choices, missing value handling",
            "intermediate": "target leakage, rolling features, aggregation windows",
            "advanced": "feature stores, online-offline consistency, drift and skew debugging",
        },
    },
    {
        "id": "ai_llm_systems",
        "name": "AI and LLM Systems",
        "focus": "prompting, grounding, retrieval, chunking, reranking, hallucination control, evaluation, routing, agent behavior",
        "examples": {
            "foundation": "prompt vs context vs retrieval",
            "intermediate": "RAG chunking, retrieval quality, prompt routing",
            "advanced": "grounding failures, evaluation design, system tradeoffs in LLM apps",
        },
    },
    {
        "id": "data_engineering",
        "name": "Data Engineering",
        "focus": "A/B tests, guardrail metrics, Simpson’s paradox, segmentation, causal traps, attribution confusion",
        "examples": {
            "foundation": "sample size intuition and vanity metrics",
            "intermediate": "why average uplift can hide segment losses",
            "advanced": "Simpson's paradox, interference effects, metric hierarchies",
        },
    },
    {
        "id": "data_pipelines",
        "name": "Data Pipelines",
        "focus": "ETL reliability, idempotency, late-arriving data, retries, data contracts, orchestration logic",
        "examples": {
            "foundation": "batch vs streaming basics with a real pipeline",
            "intermediate": "idempotent ETL and duplicate protection",
            "advanced": "late-arriving events, backfills, retry semantics, contract-driven pipelines",
        },
    },
    {
        "id": "llm_systems",
        "name": "LLM Systems",
        "focus": "RAG, chunking, retrieval quality, hallucination control, prompt routing, evaluation",
        "examples": {
            "foundation": "prompt vs context vs retrieval",
            "intermediate": "RAG chunking and reranking tradeoffs",
            "advanced": "retrieval evaluation, routing, grounding, and failure analysis",
        },
    },
    {
        "id": "statistics",
        "name": "Statistics for Decision Making",
        "focus": "sampling bias, variance, distributions, Bayesian thinking, regression pitfalls, uncertainty",
        "examples": {
            "foundation": "correlation vs causation with a sharper example",
            "intermediate": "sampling bias and misleading dashboards",
            "advanced": "Simpson's paradox, regression to the mean, calibration of uncertainty",
        },
    },
    {
        "id": "data_analytics_bi",
        "name": "Data Analytics and BI",
        "focus": "dashboard logic, KPI design, segmentation, funnel analysis, attribution, stakeholder interpretation, misleading metrics",
        "examples": {
            "foundation": "vanity metrics vs decision metrics",
            "intermediate": "funnel interpretation, segment analysis, dashboard pitfalls",
            "advanced": "metric hierarchies, attribution tradeoffs, analytical ambiguity",
        },
    },
    {
        "id": "databases_and_python",
        "name": "Databases and Python for Data",
        "focus": "database design, indexing intuition, transactional thinking, Python data workflows, dataframes, memory pitfalls",
        "examples": {
            "foundation": "primary key vs foreign key, pandas filtering basics",
            "intermediate": "indexing tradeoffs, merge pitfalls, dataframe memory mistakes",
            "advanced": "transaction boundaries, query optimization intuition, large-scale Python data workflow design",
        },
    },
]


def _tutorial_history_block(tutorial_history: list[dict], limit: int = 12) -> str:
    if not tutorial_history:
        return "(none yet)"

    lines: list[str] = []
    for entry in tutorial_history[-limit:]:
        topic = entry.get("topic_en", "")
        if not topic:
            continue
        family = entry.get("topic_family", "unknown") or "unknown"
        difficulty = entry.get("difficulty", "unknown") or "unknown"
        lines.append(f"- {topic} | family={family} | difficulty={difficulty}")

    return "\n".join(lines) if lines else "(none yet)"


def _tutorial_difficulty_for_today() -> dict:
    difficulty_key = _TUTORIAL_DIFFICULTY_SCHEDULE[datetime.now().weekday()]
    return {"key": difficulty_key, **_TUTORIAL_DIFFICULTIES[difficulty_key]}


def _tutorial_family_for_today(tutorial_history: list[dict]) -> dict:
    recent_families = [
        entry.get("topic_family")
        for entry in tutorial_history[-3:]
        if entry.get("topic_family")
    ]
    candidates = [
        family for family in _TUTORIAL_FAMILIES
        if family["id"] not in recent_families[:2]
    ] or _TUTORIAL_FAMILIES
    day_index = datetime.now().toordinal()
    return candidates[day_index % len(candidates)]


def _tutorial_recent_family_block(tutorial_history: list[dict]) -> str:
    families = []
    for entry in reversed(tutorial_history):
        family = entry.get("topic_family")
        if family and family not in families:
            families.append(family)
        if len(families) == 5:
            break
    return ", ".join(families) if families else "(none yet)"


def _tutorial_family_examples_block(family: dict) -> str:
    examples = family.get("examples", {})
    return (
        f"- Foundation angle: {examples.get('foundation', '')}\n"
        f"- Intermediate angle: {examples.get('intermediate', '')}\n"
        f"- Advanced angle: {examples.get('advanced', '')}"
    )


_TUTORIAL_PLAN_PROMPT = """\
Tutorial history (recent):
{history_block}

Recent families used:
{recent_families}

Today's assigned difficulty:
- Difficulty key: {difficulty_key}
- Difficulty label: {difficulty_label}
- Guidance: {difficulty_guidance}

Today's assigned family:
- Family id: {family_id}
- Family name: {family_name}
- Focus: {family_focus}
- Example angles:
{family_examples}

Choose ONE fresh tutorial topic for today's 8 PM Bangla Facebook lesson.

Rules:
- The topic must be specific and save-worthy
- The topic must fit the assigned family
- The topic must respect the assigned difficulty
- The assigned family is a broad domain, not a fixed menu of topics
- The example angles are inspiration only; you may choose any fresh topic inside the wider domain
- Avoid generic titles like "SQL Joins Explained" or "Decision Tree Algorithm"
- Prefer concepts that are misunderstood in practice, involve tradeoffs, or reveal a useful mental model
- The explanation later will be in simple Bengali, so pick a topic that can be made clear without dumbing it down
- Avoid exact repeats and near repeats from history

Return ONLY this JSON:
{{
  "topic_en": "specific English topic title",
  "topic_family": "{family_id}",
  "difficulty": "{difficulty_key}",
  "hook_angle": "short angle for the opening hook",
  "why_it_matters": "why this topic matters to data/AI learners",
  "learning_goal": "what the reader should understand by the end",
  "research_query": "English web research query for examples, pitfalls, and tradeoffs",
  "prereq_terms": ["term 1", "term 2", "term 3"],
  "visual_type_hint": "chart|flowchart|table|matrix|comparison|architecture",
  "visual_angle": "what the visual should teach"
}}

Rules for fields:
- prereq_terms must contain 2-4 short English terms
- visual_type_hint must be one of the listed values
- research_query must be detailed enough for Tavily research
"""


def plan_tutorial_bengali(tutorial_history: list[dict]) -> dict:
    logger.info("Planning Bengali tutorial topic...")
    difficulty = _tutorial_difficulty_for_today()
    family = _tutorial_family_for_today(tutorial_history)
    raw = _call(
        _TUTORIAL_PLAN_SYSTEM,
        _TUTORIAL_PLAN_PROMPT.format(
            history_block=_tutorial_history_block(tutorial_history),
            recent_families=_tutorial_recent_family_block(tutorial_history),
            difficulty_key=difficulty["key"],
            difficulty_label=difficulty["label"],
            difficulty_guidance=difficulty["guidance"],
            family_id=family["id"],
            family_name=family["name"],
            family_focus=family["focus"],
            family_examples=_tutorial_family_examples_block(family),
        ),
        max_tokens=1800,
    )
    result = _parse_json(raw)
    result.setdefault("example_entity", "generic")
    result.setdefault("industry", "")
    result["difficulty"] = difficulty["key"]
    result["topic_family"] = family["id"]
    result.setdefault("research_query", result.get("topic_en", "data tutorial topic"))
    logger.info(
        "Tutorial plan selected — "
        f"topic={result.get('topic_en')} | family={result.get('topic_family')} | "
        f"difficulty={result.get('difficulty')}"
    )
    return result


def _tutorial_generation_prompt(tutorial_history: list[dict], tutorial_plan: dict, research: str) -> str:
    plan_json = json.dumps(tutorial_plan, ensure_ascii=False, indent=2)
    history_block = _tutorial_history_block(tutorial_history)
    return f"""\
Tutorial history (recent):
{history_block}

Tutorial plan:
{plan_json}

Research:
{research}

Write today's Bengali Facebook tutorial.

Required learning flow:
1. Hook — 1 short paragraph about a real confusion, pain point, or scenario
2. Why it matters — 1 short paragraph tied to real work, dashboards, models, SQL, pipelines, or AI systems
3. Before we dive in — explain the key terms from the plan in simple Bengali
4. Worked example — one concrete example with realistic numbers, rows, pipeline stages, or model behavior
5. Common mistake — one practical mistake and how to avoid it
6. Mini challenge — ask the reader to predict or solve something before giving the answer
7. Takeaway — 2-3 short lines that give the mental model
8. Closing question — one natural question relevant to the lesson

Rules:
- Write in natural Bengali with occasional familiar English technical words where they sound real
- Keep the topic advanced enough to feel fresh, but keep the explanation accessible
- Use short sections and line breaks so the post is easy to read on Facebook
- Keep the full post around 450-700 words
- Use the research to ground the example, tradeoffs, and common mistake
- Do not paste URLs or source links into the tutorial post
- Avoid textbook stiffness and avoid engagement bait
- The post and the visual must align tightly
- All visual labels/data must be in English

Available visual types and best use:
- "chart" with chart_type "bar"       — comparisons, rankings, category counts
- "chart" with chart_type "line"      — trends over time, learning curves, thresholds
- "chart" with chart_type "pie"       — proportions only when proportions truly matter
- "chart" with chart_type "scatter"   — relationships, separation, calibration, tradeoffs
- "chart" with chart_type "histogram" — distributions, spread, skew
- "flowchart"                         — process logic, data flow, decision paths
- "table"                             — SQL result tables, before/after rows, feature comparisons
- "matrix"                            — confusion matrices, decision grids, metric comparisons across cells
- "comparison"                        — before/after, A vs B, wrong way vs right way
- "architecture"                      — pipeline stages, system components, RAG or ETL flow blocks

Rules for visual_config:
- Use a visual that genuinely teaches the concept
- Use meaningful values, labels, rows, or stages
- Avoid placeholder values
- Keep titles short and clear
- For scatter: provide "x_values" and "y_values"
- For histogram: provide "data"
- For flowchart: provide valid Mermaid.js syntax
- For table: provide "columns" and "rows"
- For matrix: provide "x_labels", "y_labels", and "values"
- For comparison: provide left/right titles and short bullet points
- For architecture: provide 3-6 stages with short labels/details

Return ONLY valid JSON in one of these shapes:

Chart:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "bar|line|pie|scatter|histogram", "labels": [...], "values": [...], "xlabel": "...", "ylabel": "..."}}}}

Scatter:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "scatter", "x_values": [...], "y_values": [...], "xlabel": "...", "ylabel": "..."}}}}

Histogram:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "chart", "visual_config": {{"title": "...", "chart_type": "histogram", "data": [...], "xlabel": "...", "ylabel": "Frequency"}}}}

Flowchart:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "flowchart", "visual_config": {{"title": "...", "mermaid_code": "graph TD\\n  ..."}}}}

Table:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "table", "visual_config": {{"title": "...", "columns": ["...", "..."], "rows": [["...", "..."], ["...", "..."]], "footer": "..."}}}}

Matrix:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "matrix", "visual_config": {{"title": "...", "x_labels": ["...", "..."], "y_labels": ["...", "..."], "values": [[1, 2], [3, 4]], "cell_labels": [["...", "..."], ["...", "..."]], "footer": "..."}}}}

Comparison:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "comparison", "visual_config": {{"title": "...", "left_title": "...", "right_title": "...", "left_points": ["...", "..."], "right_points": ["...", "..."], "footer": "..."}}}}

Architecture:
{{"topic_en": "...", "topic_family": "{tutorial_plan.get('topic_family', '')}", "difficulty": "{tutorial_plan.get('difficulty', '')}", "post_text": "...Bengali...", "visual_type": "architecture", "visual_config": {{"title": "...", "stages": [{{"label": "...", "detail": "..."}}, {{"label": "...", "detail": "..."}}], "footer": "..."}}}}
"""


def generate_tutorial_bengali(tutorial_history: list[dict], tutorial_plan: dict, research: str) -> dict:
    logger.info("Generating Bengali tutorial post...")
    raw = _call(
        _TUTORIAL_SYSTEM,
        _tutorial_generation_prompt(tutorial_history, tutorial_plan, research),
        max_tokens=3200,
    )
    result = _parse_json(raw)
    result["topic_family"] = tutorial_plan.get("topic_family", result.get("topic_family", ""))
    result["difficulty"] = tutorial_plan.get("difficulty", result.get("difficulty", ""))
    logger.info(
        "Tutorial generated — "
        f"topic={result.get('topic_en')} | family={result.get('topic_family')} | "
        f"difficulty={result.get('difficulty')}"
    )
    return result


# ── viral content jobs (manual cron-friendly runners) ────────────────────────

_VIRAL_SYSTEM = """\
You create high-engagement Facebook content for a Bangla-first data/AI page.
The page voice is sharp, practical, opinionated, and easy to understand.
Avoid generic motivation and avoid sounding like a content farm.
Write in natural Bengali with occasional familiar English tech words when that feels more real.
Avoid relying on the same famous company examples repeatedly.
Return valid JSON only.
"""

_VIRAL_PROMPT = """\
Create ONE viral-style Facebook post for the `{slot_name}` slot.

Slot intent:
{slot_guidance}

Assigned category for this run:
- Category: {category_name}
- Category guidance: {category_guidance}

Recent viral history:
{history_block}

Optional research/context:
{research}

Requirements:
- Pick ONE fresh, specific angle that fits the assigned category
- Make the post feel natural and not templated
- Use a strong hook in the first 1-2 lines
- The body should be concise but valuable
- Add 1 natural question or CTA at the end when it helps comments
- Keep it highly shareable/saveable
- Avoid repeating the same example company, product, or case-study setup from recent posts
- If you use a real company example, prefer a company or product not used recently
- Do NOT default to Netflix just because it is a familiar example
- Rotate across industries when useful: ecommerce, fintech, SaaS, logistics, gaming, telecom, healthcare, media, local/regional companies, productivity tools, marketplaces
- For `Mini Case Study`, you may also use a realistic generic product/business scenario instead of a famous brand

Visual requirements:
- Choose whether this post needs an illustration/image by setting visual_type to "viral"
- The image style should complement the idea using catchy cartoon-style, editorial illustration, or clean social graphic direction
- Write the image prompt in English for image generation
- Keep on-image text short

Return ONLY this JSON:
{{
  "category": "{category_name}",
  "topic_en": "short internal topic label",
  "example_entity": "company, product, or scenario name used in the post; use 'generic' if not brand-based",
  "industry": "short industry label such as streaming, fintech, ecommerce, SaaS, gaming, telecom",
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


def _viral_history_block(viral_history: list[dict] | None, limit: int = 8) -> str:
    if not viral_history:
        return "(none yet)"

    lines: list[str] = []
    for entry in viral_history[-limit:]:
        topic = entry.get("topic_en", "")
        if not topic:
            continue
        slot_name = entry.get("slot_name", "unknown") or "unknown"
        category = entry.get("category", "unknown") or "unknown"
        example_entity = entry.get("example_entity", "unknown") or "unknown"
        industry = entry.get("industry", "unknown") or "unknown"
        lines.append(
            f"- slot={slot_name} | category={category} | entity={example_entity} | "
            f"industry={industry} | topic={topic}"
        )

    return "\n".join(lines) if lines else "(none yet)"


def generate_viral_content(slot_name: str, research: str = "", viral_history: list[dict] | None = None) -> dict:
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
            history_block=_viral_history_block(viral_history),
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
