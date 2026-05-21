"""
Track tutorial history so the tutorial slot can avoid repeating both exact topics
and the same topic families too frequently.

Backward compatibility:
- data/posted_topics.json remains a simple list of topic names
- data/tutorial_history.json stores richer metadata for newer runs
- data/viral_history.json stores recent viral-content metadata
"""

import json
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

_DATA_DIR = Path("data")
_TOPICS_FILE = _DATA_DIR / "posted_topics.json"
_HISTORY_FILE = _DATA_DIR / "tutorial_history.json"
_VIRAL_HISTORY_FILE = _DATA_DIR / "viral_history.json"
_DATA_DIR.mkdir(exist_ok=True)


def _normalize_history_entry(entry) -> dict:
    if isinstance(entry, str):
        return {
            "topic_en": entry,
            "topic_family": "",
            "difficulty": "unknown",
            "learning_goal": "",
            "research_query": "",
            "posted_at": "",
        }

    if isinstance(entry, dict):
        return {
            "topic_en": entry.get("topic_en", "").strip(),
            "topic_family": entry.get("topic_family", "").strip(),
            "difficulty": entry.get("difficulty", "unknown").strip() or "unknown",
            "learning_goal": entry.get("learning_goal", "").strip(),
            "research_query": entry.get("research_query", "").strip(),
            "posted_at": entry.get("posted_at", "").strip(),
        }

    return {
        "topic_en": "",
        "topic_family": "",
        "difficulty": "unknown",
        "learning_goal": "",
        "research_query": "",
        "posted_at": "",
    }


def _read_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _normalize_viral_entry(entry) -> dict:
    if isinstance(entry, str):
        return {
            "slot_name": "",
            "category": "",
            "topic_en": entry,
            "example_entity": "",
            "industry": "",
            "posted_at": "",
        }

    if isinstance(entry, dict):
        return {
            "slot_name": entry.get("slot_name", "").strip(),
            "category": entry.get("category", "").strip(),
            "topic_en": entry.get("topic_en", "").strip(),
            "example_entity": entry.get("example_entity", "").strip(),
            "industry": entry.get("industry", "").strip(),
            "posted_at": entry.get("posted_at", "").strip(),
        }

    return {
        "slot_name": "",
        "category": "",
        "topic_en": "",
        "example_entity": "",
        "industry": "",
        "posted_at": "",
    }


def load_tutorial_history() -> list[dict]:
    raw = _read_json_file(_HISTORY_FILE, [])
    if isinstance(raw, list) and raw:
        normalized = [_normalize_history_entry(entry) for entry in raw]
        return [entry for entry in normalized if entry.get("topic_en")]

    legacy_topics = _read_json_file(_TOPICS_FILE, [])
    if isinstance(legacy_topics, list):
        normalized = [_normalize_history_entry(topic) for topic in legacy_topics]
        return [entry for entry in normalized if entry.get("topic_en")]

    return []


def load_posted_topics() -> list[str]:
    history = load_tutorial_history()
    if history:
        return [entry["topic_en"] for entry in history if entry.get("topic_en")]

    raw = _read_json_file(_TOPICS_FILE, [])
    if isinstance(raw, list):
        return [str(topic) for topic in raw]
    return []


def load_viral_history() -> list[dict]:
    raw = _read_json_file(_VIRAL_HISTORY_FILE, [])
    if not isinstance(raw, list):
        return []

    normalized = [_normalize_viral_entry(entry) for entry in raw]
    return [entry for entry in normalized if entry.get("topic_en")]


def mark_topic_posted(topic) -> None:
    entry = _normalize_history_entry(topic)
    topic_en = entry["topic_en"]
    if not topic_en:
        return

    history = load_tutorial_history()
    if any(existing.get("topic_en") == topic_en for existing in history):
        return

    entry["posted_at"] = entry["posted_at"] or datetime.now().isoformat(timespec="seconds")
    history.append(entry)

    _HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _TOPICS_FILE.write_text(
        json.dumps([item["topic_en"] for item in history], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Tutorial saved to tracker: "
        f"{topic_en} | family={entry.get('topic_family') or 'n/a'} | "
        f"difficulty={entry.get('difficulty') or 'n/a'}"
    )


def mark_viral_posted(post) -> None:
    entry = _normalize_viral_entry(post)
    topic_en = entry["topic_en"]
    if not topic_en:
        return

    history = load_viral_history()
    if any(
        existing.get("topic_en") == topic_en
        and existing.get("slot_name") == entry.get("slot_name")
        for existing in history
    ):
        return

    entry["posted_at"] = entry["posted_at"] or datetime.now().isoformat(timespec="seconds")
    history.append(entry)
    _VIRAL_HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Viral post saved to tracker: "
        f"{topic_en} | slot={entry.get('slot_name') or 'n/a'} | "
        f"entity={entry.get('example_entity') or 'n/a'}"
    )
