"""
Tracks tutorial topics that have already been posted so Claude never repeats one.
Persists to data/posted_topics.json.
"""

import json
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

_DATA_DIR   = Path("data")
_TOPICS_FILE = _DATA_DIR / "posted_topics.json"
_DATA_DIR.mkdir(exist_ok=True)


def load_posted_topics() -> list[str]:
    if not _TOPICS_FILE.exists():
        return []
    try:
        return json.loads(_TOPICS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def mark_topic_posted(topic_en: str) -> None:
    topics = load_posted_topics()
    if topic_en not in topics:
        topics.append(topic_en)
        _TOPICS_FILE.write_text(
            json.dumps(topics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Topic saved to tracker: {topic_en}")
