from tavily import TavilyClient
from config import TAVILY_API_KEY, RESEARCH_TOPIC
from utils.logger import get_logger

logger = get_logger(__name__)

_client = TavilyClient(api_key=TAVILY_API_KEY)


def research_topic(topic: str | None = None) -> str:
    """Search Tavily for the latest content on `topic` and return a compiled summary."""
    query = topic or RESEARCH_TOPIC
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
