"""
Facebook Auto-Poster — entry point.

Runs an APScheduler that fires 3 jobs per day (configurable via POST_TIMES in .env).
The slot defined by VISUAL_POST_INDEX gets an AI-generated visual attached.

Usage:
  python main.py                  # start the scheduler (runs forever)
  python main.py --test 0         # immediately run slot 0 (text post)
  python main.py --test 2         # immediately run slot 2 (visual post, by default)
"""

import argparse
import os
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import POST_TIMES, RESEARCH_TOPIC, TIMEZONE, VISUAL_POST_INDEX
from agents.researcher import research_topic
from agents.writer import generate_text_post, generate_visual_post
from agents.visual import generate_visual
from poster.facebook import post_text, post_with_image
from utils.logger import get_logger

logger = get_logger("main")


def run_post_job(slot_index: int) -> None:
    """Full pipeline for one scheduled post slot."""
    total = len(POST_TIMES)
    logger.info(f"=== Starting post job: slot {slot_index + 1}/{total} ===")

    try:
        # 1. Research
        research = research_topic(RESEARCH_TOPIC)

        # 2. Generate content
        is_visual = (slot_index == VISUAL_POST_INDEX)
        content = (
            generate_visual_post(research, RESEARCH_TOPIC)
            if is_visual
            else generate_text_post(research, RESEARCH_TOPIC)
        )

        post_message = content["post_text"]
        visual_type  = content.get("visual_type", "none")
        visual_cfg   = content.get("visual_config", {})

        # 3. Post
        if visual_type and visual_type != "none":
            image_path = generate_visual(visual_type, visual_cfg)
            result = post_with_image(post_message, image_path)
            # Clean up the temp image after upload
            try:
                os.remove(image_path)
            except OSError:
                pass
        else:
            result = post_text(post_message)

        logger.info(f"=== Slot {slot_index + 1} done — post id: {result.get('id', 'N/A')} ===")

    except Exception:
        logger.exception(f"Slot {slot_index + 1} failed — will retry at next scheduled time")


def build_scheduler() -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    for i, time_str in enumerate(POST_TIMES):
        hour, minute = map(int, time_str.split(":"))
        is_visual = (i == VISUAL_POST_INDEX)
        scheduler.add_job(
            run_post_job,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
            args=[i],
            id=f"slot_{i}",
            name=f"Post slot {i + 1} {'[+visual]' if is_visual else '[text]'}",
            misfire_grace_time=300,
            coalesce=True,
        )
        logger.info(
            f"  Scheduled slot {i + 1} at {time_str} {TIMEZONE} "
            f"{'← includes visual' if is_visual else ''}"
        )

    return scheduler


def main() -> None:
    parser = argparse.ArgumentParser(description="Facebook Auto-Poster")
    parser.add_argument(
        "--test",
        metavar="SLOT",
        type=int,
        help="Run a single slot immediately and exit (0-indexed)",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Facebook Auto-Poster starting")
    logger.info(f"  Topic    : {RESEARCH_TOPIC}")
    logger.info(f"  Schedule : {', '.join(POST_TIMES)} ({TIMEZONE})")
    logger.info(f"  Visual   : slot {VISUAL_POST_INDEX + 1} of {len(POST_TIMES)}")
    logger.info("=" * 60)

    if args.test is not None:
        slot = args.test
        if slot < 0 or slot >= len(POST_TIMES):
            logger.error(f"--test slot must be 0–{len(POST_TIMES) - 1}")
            sys.exit(1)
        logger.info(f"TEST MODE: running slot {slot + 1} immediately")
        run_post_job(slot)
        return

    scheduler = build_scheduler()
    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
