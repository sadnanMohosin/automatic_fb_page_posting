"""
Facebook Graph API poster.

Posts text-only or text+image content to a Facebook Page.
Requires a long-lived Page Access Token with `pages_manage_posts` permission.

Token refresh reminder: long-lived tokens last ~60 days.
Rotate yours before expiry to avoid missed posts.
"""

import time
from datetime import datetime, timedelta, timezone

import requests

from config import FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID
from utils.logger import get_logger

logger = get_logger(__name__)

_GRAPH_VERSION = "v19.0"
_BASE = f"https://graph.facebook.com/{_GRAPH_VERSION}"
_REQUEST_TIMEOUT = 60
_RETRY_DELAYS = (2, 5, 10)
_RECENT_POST_LOOKBACK_SECONDS = 900
_RECENT_POST_SCAN_LIMIT = 10


class FacebookAPIError(RuntimeError):
    def __init__(self, code, message, err_type=None, fbtrace_id=None, payload=None):
        super().__init__(
            f"Facebook API error {code}: {message} "
            f"(type={err_type}, fbtrace_id={fbtrace_id})"
        )
        self.code = code
        self.message = message
        self.err_type = err_type
        self.fbtrace_id = fbtrace_id
        self.payload = payload or {}


def _is_retryable_facebook_error(exc: Exception) -> bool:
    if isinstance(exc, requests.RequestException):
        return True
    if isinstance(exc, FacebookAPIError):
        return exc.code in {1, 2, 4, 17, 341}
    return False


def _check_response(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {}

    if "error" in data:
        err = data["error"]
        raise FacebookAPIError(
            code=err.get("code"),
            message=err.get("message"),
            err_type=err.get("type"),
            fbtrace_id=err.get("fbtrace_id"),
            payload=data,
        )
    return data


def _parse_facebook_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _find_recent_matching_post(message: str) -> dict | None:
    message = (message or "").strip()
    if not message:
        return None

    url = f"{_BASE}/{FB_PAGE_ID}/posts"
    resp = requests.get(
        url,
        params={
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,message,created_time",
            "limit": _RECENT_POST_SCAN_LIMIT,
        },
        timeout=_REQUEST_TIMEOUT,
    )
    data = _check_response(resp)
    now = datetime.now(timezone.utc)

    for post in data.get("data", []):
        if (post.get("message") or "").strip() != message:
            continue
        created_at = _parse_facebook_time(post.get("created_time", ""))
        if created_at and now - created_at <= timedelta(seconds=_RECENT_POST_LOOKBACK_SECONDS):
            return post
    return None


def _post_with_retries(url: str, *, data: dict, files_factory=None) -> dict:
    attempts = len(_RETRY_DELAYS) + 1

    for attempt in range(1, attempts + 1):
        try:
            if files_factory:
                with files_factory() as files:
                    resp = requests.post(url, data=data, files=files, timeout=_REQUEST_TIMEOUT)
            else:
                resp = requests.post(url, data=data, timeout=_REQUEST_TIMEOUT)
            return _check_response(resp)
        except Exception as exc:
            if isinstance(exc, FacebookAPIError):
                try:
                    existing_post = _find_recent_matching_post(data.get("message", ""))
                except Exception as lookup_exc:
                    logger.warning(f"Recent-post duplicate check failed: {lookup_exc}")
                else:
                    if existing_post:
                        logger.warning(
                            "Facebook returned an error, but a matching recent post already exists; "
                            f"treating it as success with id={existing_post.get('id')}"
                        )
                        return existing_post

            if attempt >= attempts or not _is_retryable_facebook_error(exc):
                raise

            delay = _RETRY_DELAYS[attempt - 1]
            logger.warning(
                f"Facebook post attempt {attempt}/{attempts} failed ({exc}); retrying in {delay}s"
            )
            time.sleep(delay)


def post_text(message: str) -> dict:
    """Publish a text-only post to the Facebook Page feed."""
    url = f"{_BASE}/{FB_PAGE_ID}/feed"
    result = _post_with_retries(
        url,
        data={
            "message": message,
            "access_token": FB_PAGE_ACCESS_TOKEN,
        },
    )
    logger.info(f"Text post published - id={result.get('id')}")
    return result


def post_with_image(message: str, image_path: str) -> dict:
    """
    Publish a post with an attached image to the Facebook Page.

    The image is uploaded via multipart form (source field) and published
    immediately together with the caption in one API call.
    """
    url = f"{_BASE}/{FB_PAGE_ID}/photos"

    def _files_factory():
        img_file = open(image_path, "rb")

        class _UploadContext:
            def __enter__(self_inner):
                return {"source": img_file}

            def __exit__(self_inner, exc_type, exc, tb):
                img_file.close()

        return _UploadContext()

    result = _post_with_retries(
        url,
        data={
            "message": message,
            "access_token": FB_PAGE_ACCESS_TOKEN,
        },
        files_factory=_files_factory,
    )
    logger.info(f"Photo post published - id={result.get('id')}")
    return result
