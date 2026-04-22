"""
Facebook Token Refresher
------------------------
Exchanges a short-lived User Token for a never-expiring Page Access Token
and writes it back to .env automatically.

Usage:
  1. Add to .env:
       FB_APP_ID=your_app_id
       FB_APP_SECRET=your_app_secret
       FB_SHORT_USER_TOKEN=paste_fresh_short_token_here

  2. Run:
       python refresh_token.py

  3. FB_PAGE_ACCESS_TOKEN in .env is updated automatically.

How to get FB_SHORT_USER_TOKEN:
  Go to Graph API Explorer → select your app → click "Generate Access Token"
  → grant pages_manage_posts + pages_read_engagement → copy the token shown.
  This token lasts ~1 hour but that's enough to run this script.

Note: Page Access Tokens obtained this way never expire as long as you don't
change your Facebook password or revoke the app.
"""

import os
import sys
from pathlib import Path

import requests

GRAPH_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def _read_env(env_path: Path) -> dict:
    data = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _write_env(env_path: Path, updates: dict) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    written_keys = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            written_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in written_keys:
            new_lines.append(f"{key}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _check(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response ({resp.status_code}): {resp.text}")
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error", {})
        raise RuntimeError(f"Facebook API error {err.get('code')}: {err.get('message')} (type={err.get('type')})")
    return data


def _get_long_lived_user_token(app_id: str, app_secret: str, short_token: str) -> str:
    data = _check(requests.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }, timeout=30))
    return data["access_token"]


def _get_page_token(long_lived_user_token: str, page_id: str) -> dict:
    data = _check(requests.get(f"{GRAPH_BASE}/me/accounts", params={
        "access_token": long_lived_user_token,
    }, timeout=30))
    pages = data.get("data", [])
    if not pages:
        raise RuntimeError("No pages found for this user token.")
    for page in pages:
        if page.get("id") == page_id:
            return page
    names = ", ".join(f"{p['name']} ({p['id']})" for p in pages)
    raise RuntimeError(f"Page ID {page_id} not found. Available pages: {names}")


def main():
    env_path = Path(".env")
    env = _read_env(env_path)

    app_id      = os.getenv("FB_APP_ID")      or env.get("FB_APP_ID")
    app_secret  = os.getenv("FB_APP_SECRET")  or env.get("FB_APP_SECRET")
    short_token = os.getenv("FB_SHORT_USER_TOKEN") or env.get("FB_SHORT_USER_TOKEN")
    page_id     = os.getenv("FB_PAGE_ID")     or env.get("FB_PAGE_ID")

    missing = [k for k, v in {
        "FB_APP_ID": app_id,
        "FB_APP_SECRET": app_secret,
        "FB_SHORT_USER_TOKEN": short_token,
        "FB_PAGE_ID": page_id,
    }.items() if not v]

    if missing:
        raise RuntimeError("Missing required values in .env: " + ", ".join(missing))

    print("Step 1/3 — Exchanging short-lived token for long-lived user token...")
    long_user_token = _get_long_lived_user_token(app_id, app_secret, short_token)
    print("         Long-lived user token received (valid ~60 days).")

    print("Step 2/3 — Fetching never-expiring Page Access Token...")
    page = _get_page_token(long_user_token, page_id)
    page_token = page["access_token"]
    print(f"         Page found: {page.get('name')} ({page['id']})")

    print("Step 3/3 — Writing FB_PAGE_ACCESS_TOKEN to .env...")
    _write_env(env_path, {"FB_PAGE_ACCESS_TOKEN": page_token})

    print("\nDone. FB_PAGE_ACCESS_TOKEN updated in .env.")
    print("This Page Access Token never expires (unless you change your FB password).")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
