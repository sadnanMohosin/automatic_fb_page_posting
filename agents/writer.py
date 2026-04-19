import json
import re
import anthropic
from config import ANTHROPIC_API_KEY, RESEARCH_TOPIC
from utils.logger import get_logger

logger = get_logger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM = """\
You are a professional social media content writer specializing in Facebook pages.
Write engaging, informative posts based on research summaries provided to you.

Style rules:
- Conversational and engaging tone; avoid sounding like a press release
- 150–400 words per post
- Include 3–5 relevant hashtags at the end
- Use line breaks for readability
- Lead with a hook (question, bold statement, or surprising fact)

Always return ONLY a valid JSON object — no markdown, no code fences, no commentary.
"""

_TEXT_PROMPT = """\
Research summary (topic: {topic}):
{research}

Write an engaging Facebook post based on this research.

Return this exact JSON structure:
{{"post_text": "<your full post content with hashtags>", "visual_type": "none"}}
"""

_VISUAL_PROMPT = """\
Research summary (topic: {topic}):
{research}

Write an engaging Facebook post that includes a visual element.
Choose the visual type that best suits the content:

- "chart"     → data/statistics → bar, line, or pie chart with real data points
- "flowchart" → process/how-to → Mermaid.js diagram
- "image"     → story/concept  → AI-generated illustration

Return ONLY one of these three JSON structures (no other text):

For chart:
{{"post_text":"...","visual_type":"chart","visual_config":{{"title":"...","chart_type":"bar|line|pie","labels":["A","B","C"],"values":[10,20,30],"xlabel":"...","ylabel":"..."}}}}

For flowchart:
{{"post_text":"...","visual_type":"flowchart","visual_config":{{"title":"...","mermaid_code":"graph TD\\n  A[Start] --> B[Step]\\n  B --> C[End]"}}}}

For image:
{{"post_text":"...","visual_type":"image","visual_config":{{"title":"...","prompt":"detailed, vivid image generation prompt (no text/logos)"}}}}
"""


def _parse_json(raw: str) -> dict:
    """Strip code fences if present and parse JSON."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw.strip())


def generate_text_post(research: str, topic: str | None = None) -> dict:
    """Generate a text-only Facebook post. Returns dict with post_text and visual_type='none'."""
    logger.info("Generating text post...")
    prompt = _TEXT_PROMPT.format(topic=topic or RESEARCH_TOPIC, research=research)

    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _parse_json(msg.content[0].text)
    logger.info("Text post generated.")
    return result


def generate_visual_post(research: str, topic: str | None = None) -> dict:
    """Generate a Facebook post with a visual. Returns dict with post_text, visual_type, visual_config."""
    logger.info("Generating visual post...")
    prompt = _VISUAL_PROMPT.format(topic=topic or RESEARCH_TOPIC, research=research)

    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    result = _parse_json(msg.content[0].text)
    logger.info(f"Visual post generated — visual_type={result.get('visual_type')}")
    return result
