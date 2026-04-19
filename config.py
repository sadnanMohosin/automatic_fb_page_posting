import os
import sys
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        print(f"ERROR: Missing required environment variable: {key}", file=sys.stderr)
        print(f"       Copy .env.example to .env and fill in your keys.", file=sys.stderr)
        sys.exit(1)
    return value

# Required
TAVILY_API_KEY        = _require("TAVILY_API_KEY")
ANTHROPIC_API_KEY     = _require("ANTHROPIC_API_KEY")
FB_PAGE_ACCESS_TOKEN  = _require("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID            = _require("FB_PAGE_ID")

# Optional with defaults
GOOGLE_API_KEY        = os.getenv("GOOGLE_API_KEY", "")
RESEARCH_TOPIC        = os.getenv("RESEARCH_TOPIC", "technology news and AI trends")
TIMEZONE              = os.getenv("TIMEZONE", "UTC")
VISUAL_POST_INDEX     = int(os.getenv("VISUAL_POST_INDEX", "2"))

_raw_times = os.getenv("POST_TIMES", "08:00,14:00,20:00")
POST_TIMES = [t.strip() for t in _raw_times.split(",") if t.strip()]

if not POST_TIMES:
    POST_TIMES = ["08:00", "14:00", "20:00"]
