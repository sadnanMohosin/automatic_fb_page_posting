"""
Facebook Auto-Poster — entry point.

Daily schedule (Asia/Dhaka / Bangladesh time):
  10:00 AM  → slot 0: Tech news digest     — 3 top tech/AI updates with image
  08:00 PM  → slot 1: Bengali tutorial     — data/ML/AI lesson in Bengali + chart/flowchart
  11:00 PM  → quote slot disabled for now

Usage:
  python main.py              # start the scheduler (runs forever)
  python main.py --test 0     # run slot 0 (news digest) immediately and exit
  python main.py --test 1     # run slot 1 (Bengali tutorial) immediately and exit
  python main.py --test v1    # run viral day content immediately and exit
  python main.py --test v2    # run viral night content immediately and exit
"""

import argparse
import os
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POST_TIMES, TIMEZONE
from agents.researcher import research_topic
from agents.writer import (
    generate_news_digest,
    generate_tutorial_bengali,
    generate_viral_content,
)
from agents.visual import generate_visual
from agents.topic_tracker import load_posted_topics, mark_topic_posted
from poster.facebook import post_with_image
from utils.logger import get_logger

logger = get_logger("main")

# ── slot handlers ─────────────────────────────────────────────────────────────

def run_news_digest() -> None:
    """10 AM BD — research top 3 tech/AI news and post with cover image."""
    logger.info("=== [Slot 1] Tech News Digest ===")
    research   = research_topic("top technology AI news updates today")
    content    = generate_news_digest(research)
    headlines  = content.get("headlines", [])
    image_path = generate_visual("news", {"headlines": headlines})
    result     = post_with_image(content["post_text"], image_path)
    try:
        os.remove(image_path)
    except OSError:
        pass
    logger.info(f"News digest posted — id: {result.get('id')}")


def run_tutorial() -> None:
    """8 PM BD — Bengali tutorial on data/ML/AI with chart or flowchart."""
    logger.info("=== [Slot 2] Bengali Tutorial ===")

    posted_topics = load_posted_topics()
    content = generate_tutorial_bengali(posted_topics)

    topic_en    = content["topic_en"]
    post_msg    = content["post_text"]
    visual_type = content.get("visual_type", "chart")
    visual_cfg  = content.get("visual_config", {})

    image_path = generate_visual(visual_type, visual_cfg)
    result = post_with_image(post_msg, image_path)

    # Record the topic so it's never repeated
    mark_topic_posted(topic_en)

    try:
        os.remove(image_path)
    except OSError:
        pass

    logger.info(f"Tutorial posted — topic: {topic_en} | id: {result.get('id')}")


def run_viral_day() -> None:
    """Manual cron job — discussion-friendly daytime viral content."""
    logger.info("=== [Manual Job] Viral Day Content ===")
    research = research_topic("latest AI technology business and data career developments today")
    content = generate_viral_content("day", research=research)
    image_path = generate_visual(content.get("visual_type", "viral"), content.get("visual_config", {}))
    result = post_with_image(content["post_text"], image_path)

    try:
        os.remove(image_path)
    except OSError:
        pass

    logger.info(f"Viral day post published — category: {content.get('category')} | id: {result.get('id')}")


def run_viral_night() -> None:
    """Manual cron job — save-worthy nighttime viral content."""
    logger.info("=== [Manual Job] Viral Night Content ===")
    content = generate_viral_content("night")
    image_path = generate_visual(content.get("visual_type", "viral"), content.get("visual_config", {}))
    result = post_with_image(content["post_text"], image_path)

    try:
        os.remove(image_path)
    except OSError:
        pass

    logger.info(f"Viral night post published — category: {content.get('category')} | id: {result.get('id')}")


# ── slot dispatch table ───────────────────────────────────────────────────────

_SCHEDULED_SLOTS = [
    {"fn": run_news_digest,        "label": "Tech News Digest  [10:00 AM BD]"},
    {"fn": run_tutorial,           "label": "Bengali Tutorial  [08:00 PM BD]"},
    # {"fn": run_motivational_quote, "label": "Motivational Quote [11:00 PM BD]"},
]

_MANUAL_JOBS = {
    "viral_day": {"fn": run_viral_day, "label": "Viral Day Content"},
    "viral_night": {"fn": run_viral_night, "label": "Viral Night Content"},
}

_TEST_TARGETS = {
    "0": {"fn": lambda: _safe_run(0), "label": "Tech News Digest"},
    "1": {"fn": lambda: _safe_run(1), "label": "Bengali Tutorial"},
    "v1": {"fn": lambda: _safe_named_run("Viral Day Content", run_viral_day), "label": "Viral Day Content"},
    "v2": {"fn": lambda: _safe_named_run("Viral Night Content", run_viral_night), "label": "Viral Night Content"},
}


def _safe_run(slot_index: int) -> None:
    slot = _SCHEDULED_SLOTS[slot_index]
    try:
        slot["fn"]()
    except Exception:
        logger.exception(f"Slot {slot_index} ({slot['label']}) failed — will retry next scheduled time")


# ── scheduler ─────────────────────────────────────────────────────────────────

def _safe_named_run(label: str, fn) -> None:
    try:
        fn()
    except Exception:
        logger.exception(f"{label} failed")


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    for i, (time_str, slot) in enumerate(zip(POST_TIMES, _SCHEDULED_SLOTS)):
        hour, minute = map(int, time_str.split(":"))
        scheduler.add_job(
            _safe_run,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
            args=[i],
            id=f"slot_{i}",
            name=slot["label"],
            misfire_grace_time=300,
            coalesce=True,
        )
        logger.info(f"  Scheduled: {slot['label']} at {time_str} {TIMEZONE}")

    return scheduler


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Facebook Auto-Poster")
    parser.add_argument(
        "--test",
        metavar="TARGET",
        choices=sorted(_TEST_TARGETS.keys()),
        help="Run a target immediately and exit (0=news, 1=tutorial, v1=viral_day, v2=viral_night)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Facebook Auto-Poster — Bangladesh Schedule")
    for i, (t, s) in enumerate(zip(POST_TIMES, _SCHEDULED_SLOTS)):
        logger.info(f"  {t} {TIMEZONE}  →  {s['label']}")
    logger.info("  Quote slot disabled for now.")
    for job_name, job in _MANUAL_JOBS.items():
        logger.info(f"  Manual job: {job_name}  →  {job['label']}")
    logger.info("=" * 60)

    if args.test:
        logger.info(f"TEST MODE: running {args.test} immediately")
        _TEST_TARGETS[args.test]["fn"]()
        return

    scheduler = build_scheduler()
    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
