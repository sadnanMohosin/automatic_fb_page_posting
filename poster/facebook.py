"""
Facebook Graph API poster.

Posts text-only or text+image content to a Facebook Page.
Requires a long-lived Page Access Token with `pages_manage_posts` permission.

Token refresh reminder: long-lived tokens last ~60 days.
Rotate yours before expiry to avoid missed posts.
"""

import requests
from config import FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID
from utils.logger import get_logger

logger = get_logger(__name__)

_GRAPH_VERSION = "v19.0"
_BASE = f"https://graph.facebook.com/{_GRAPH_VERSION}"


def _check_response(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {}

    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"Facebook API error {err.get('code')}: {err.get('message')} "
            f"(type={err.get('type')}, fbtrace_id={err.get('fbtrace_id')})"
        )
    return data


def post_text(message: str) -> dict:
    """Publish a text-only post to the Facebook Page feed."""
    url = f"{_BASE}/{FB_PAGE_ID}/feed"
    resp = requests.post(url, data={
        "message": message,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    })
    result = _check_response(resp)
    logger.info(f"Text post published — id={result.get('id')}")
    return result


def post_with_image(message: str, image_path: str) -> dict:
    """
    Publish a post with an attached image to the Facebook Page.

    The image is uploaded via multipart form (source field) and published
    immediately together with the caption in one API call.
    """
    url = f"{_BASE}/{FB_PAGE_ID}/photos"
    with open(image_path, "rb") as img_file:
        resp = requests.post(
            url,
            files={"source": img_file},
            data={
                "message": message,
                "access_token": FB_PAGE_ACCESS_TOKEN,
            },
        )
    result = _check_response(resp)
    logger.info(f"Photo post published — id={result.get('id')}")
    return result
