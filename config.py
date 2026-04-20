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
TAVILY_API_KEY       = _require("TAVILY_API_KEY")
ANTHROPIC_API_KEY    = _require("ANTHROPIC_API_KEY")
FB_PAGE_ACCESS_TOKEN = _require("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID           = _require("FB_PAGE_ID")

# Optional
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Schedule — defaults to BD times in Asia/Dhaka
TIMEZONE   = os.getenv("TIMEZONE", "Asia/Dhaka")
POST_TIMES = [t.strip() for t in os.getenv("POST_TIMES", "10:00,20:00,23:00").split(",") if t.strip()]
