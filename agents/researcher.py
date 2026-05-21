from tavily import TavilyClient
from config import TAVILY_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

_client = TavilyClient(api_key=TAVILY_API_KEY)
_MAX_TAVILY_QUERY_LEN = 380


def _compact_query(text: str, max_len: int = _MAX_TAVILY_QUERY_LEN) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_len:
        return compact

    trimmed = compact[:max_len].rsplit(" ", 1)[0].strip()
    return trimmed or compact[:max_len]


def research_topic(topic: str) -> str:
    """Search Tavily for the latest content on `topic` and return a compiled summary."""
    query = _compact_query(topic)
    logger.info(f"Researching: '{query}'")

    response = _client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True,
        include_raw_content=False,
    )

    parts: list[str] = []

    if response.get("answer"):
        parts.append(f"Key Insight:\n{response['answer']}")

    for r in response.get("results", []):
        title = r.get("title", "Untitled")
        content = (r.get("content") or "")[:600].strip()
        url = r.get("url", "")
        if content:
            parts.append(f"Source: {title}\nURL: {url}\n{content}")

    summary = "\n\n---\n\n".join(parts)
    logger.info(f"Research done — {len(response.get('results', []))} sources, {len(summary)} chars")
    return summary


def research_tutorial_topic(
    topic_en: str,
    topic_family: str = "",
    difficulty: str = "intermediate",
    learning_goal: str = "",
) -> str:
    """Research practical examples, mistakes, and tradeoffs for a tutorial topic."""
    family_hint = f"{topic_family} " if topic_family else ""
    goal_hint = ""
    if learning_goal:
        goal_hint = _compact_query(learning_goal, max_len=120)
        goal_hint = f" key goal: {goal_hint}"

    query = (
        f"{topic_en} {family_hint}practical examples pitfalls tradeoffs "
        f"{difficulty} explanation{goal_hint}"
    )
    return research_topic(query)
