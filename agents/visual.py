"""
Visual generation module.

  chart      → Matplotlib (free, local)           — used for tutorial data visuals
  flowchart  → mermaid.ink API (free, no auth)    — used for tutorial process diagrams
  quote      → Matplotlib dark-bg text image      — archived quote image renderer
  image      → Google Imagen 4 (optional)         — generic AI image
  viral      → illustration-first social image    — viral/career/news opinion posts
"""

import base64
import importlib
import os
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # must be set before pyplot import
import matplotlib.pyplot as plt
import requests

from config import GOOGLE_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)

_VISUALS_DIR = Path("visuals")
_VISUALS_DIR.mkdir(exist_ok=True)

_FACEBOOK_BLUE  = "#1877F2"
_FACEBOOK_GRAY  = "#E4E6EB"
_PALETTE = ["#1877F2", "#42B72A", "#F02849", "#F7B928", "#898F9C", "#4267B2"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _package_version(dist_name: str) -> str | None:
    try:
        return version(dist_name)
    except PackageNotFoundError:
        return None


def _google_sdk_summary() -> str:
    installed = []
    for dist_name in ("google-genai", "google-generativeai", "google-ai-generativelanguage", "google"):
        dist_version = _package_version(dist_name)
        if dist_version:
            installed.append(f"{dist_name}={dist_version}")
    return ", ".join(installed) if installed else "none detected"


def _load_google_genai_sdk():
    try:
        genai = importlib.import_module("google.genai")
        types = importlib.import_module("google.genai.types")
        return genai, types
    except Exception as exc:
        raise RuntimeError(
            "Google GenAI SDK import failed. This code expects the `google-genai` package "
            "and the `google.genai` module. Installed Google SDKs: "
            f"{_google_sdk_summary()}. Reinstall `google-genai` in the active environment "
            "and remove conflicting packages such as `google-generativeai` or the standalone "
            "`google` package if they are shadowing the namespace."
        ) from exc


def _find_base64_image_payload(node) -> str | None:
    if isinstance(node, dict):
        for key in ("bytesBase64Encoded", "imageBytes"):
            value = node.get(key)
            if isinstance(value, str) and value:
                return value
        for value in node.values():
            found = _find_base64_image_payload(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_base64_image_payload(item)
            if found:
                return found
    return None


def _generate_google_image_rest(prompt: str, out_path: Path, aspect_ratio: str = "1:1") -> str:
    """Generate an image via the official Imagen REST endpoint when the SDK path is unavailable."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": "allow_adult",
        },
    }

    resp = requests.post(
        url,
        headers={
            "x-goog-api-key": GOOGLE_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError("Google Imagen REST returned a non-JSON response")

    if "error" in data:
        err = data["error"]
        raise RuntimeError(
            f"Google Imagen REST error {err.get('code')}: {err.get('message')}"
        )

    image_b64 = _find_base64_image_payload(data)
    if not image_b64:
        raise RuntimeError("Google Imagen REST returned no image bytes in the response payload")

    out_path.write_bytes(base64.b64decode(image_b64))
    return str(out_path)


# ── chart ─────────────────────────────────────────────────────────────────────

def generate_chart(config: dict) -> str:
    title      = config.get("title", "Overview")
    chart_type = config.get("chart_type", "bar")
    labels     = config.get("labels", ["A", "B", "C"])
    values     = config.get("values", [1, 2, 3])
    xlabel     = config.get("xlabel", "")
    ylabel     = config.get("ylabel", "")

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#f8f9fa")
    ax.set_facecolor("#ffffff")

    colors = _PALETTE[: len(labels)]

    x_values   = config.get("x_values", [])
    y_values   = config.get("y_values", [])
    hist_data  = config.get("data", [])

    if chart_type == "bar":
        bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=1.5, width=0.6)
        ax.bar_label(bars, padding=4, fontsize=11, fontweight="bold")
        ax.set_ylim(0, max(values) * 1.2)
    elif chart_type == "line":
        ax.plot(labels, values, color=_FACEBOOK_BLUE, linewidth=2.5,
                marker="o", markersize=8, markerfacecolor="white", markeredgewidth=2.5)
        ax.fill_between(range(len(labels)), values, alpha=0.08, color=_FACEBOOK_BLUE)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels)
        ax.set_ylim(0, max(values) * 1.2)
    elif chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors,
            autopct="%1.1f%%", startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
        )
        for at in autotexts:
            at.set_fontweight("bold")
            at.set_fontsize(11)
    elif chart_type == "scatter":
        ax.scatter(x_values, y_values, color=_FACEBOOK_BLUE, s=80, alpha=0.75, edgecolors="white", linewidth=0.8)
        ax.set_xlim(min(x_values) * 0.9, max(x_values) * 1.1)
        ax.set_ylim(min(y_values) * 0.9, max(y_values) * 1.1)
    elif chart_type == "histogram":
        import numpy as np
        ax.hist(hist_data, bins="auto", color=_FACEBOOK_BLUE, edgecolor="white", linewidth=0.8, alpha=0.85)
        ax.set_ylim(0, None)

    ax.set_title(title, fontsize=16, fontweight="bold", pad=16, color="#1c1e21")
    if xlabel and chart_type != "pie":
        ax.set_xlabel(xlabel, fontsize=12, color="#606770")
    if ylabel and chart_type != "pie":
        ax.set_ylabel(ylabel, fontsize=12, color="#606770")

    if chart_type != "pie":
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(colors="#606770")

    plt.tight_layout()
    out = _VISUALS_DIR / f"chart_{_ts()}.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    logger.info(f"Chart saved → {out}")
    return str(out)


# ── flowchart ─────────────────────────────────────────────────────────────────

def generate_flowchart(config: dict) -> str:
    mermaid_code = config.get("mermaid_code", "graph TD\n  A[Start] --> B[End]")

    # mermaid.ink renders Mermaid diagrams as PNG for free
    encoded = base64.urlsafe_b64encode(mermaid_code.encode()).decode()
    url = f"https://mermaid.ink/img/{encoded}?bgColor=f8f9fa"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"mermaid.ink failed ({exc}); falling back to plain chart")
        return generate_chart({
            "title": config.get("title", "Process Overview"),
            "chart_type": "bar",
            "labels": ["Step 1", "Step 2", "Step 3"],
            "values": [33, 33, 34],
            "ylabel": "Completion %",
        })

    out = _VISUALS_DIR / f"flowchart_{_ts()}.png"
    out.write_bytes(resp.content)
    logger.info(f"Flowchart saved → {out}")
    return str(out)


# ── AI image ──────────────────────────────────────────────────────────────────

def _generate_google_image(prompt: str, out_path: Path, aspect_ratio: str = "1:1") -> str:
    """Generate an image with Google's current GenAI SDK and save it locally."""
    sdk_error = None

    try:
        genai, types = _load_google_genai_sdk()

        client = genai.Client(api_key=GOOGLE_API_KEY)
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                person_generation="allow_adult",
                output_mime_type="image/png",
                enhance_prompt=True,
            ),
        )

        if not response.generated_images:
            raise RuntimeError("Google GenAI returned no images")

        response.generated_images[0].image.save(str(out_path))
        return str(out_path)
    except Exception as exc:
        sdk_error = exc
        logger.warning(f"Google GenAI SDK path failed ({exc}); trying REST fallback")

    try:
        return _generate_google_image_rest(prompt, out_path, aspect_ratio=aspect_ratio)
    except Exception as rest_exc:
        raise RuntimeError(
            f"Google image generation failed via SDK ({sdk_error}) and REST ({rest_exc})"
        ) from rest_exc

def generate_ai_image(config: dict) -> str:
    prompt = config.get("prompt", "A professional technology concept illustration, clean and modern")

    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set — falling back to Matplotlib chart")
        return _fallback_chart(config)

    try:
        out = _VISUALS_DIR / f"image_{_ts()}.png"
        _generate_google_image(prompt, out, aspect_ratio="1:1")
        logger.info(f"AI image saved → {out}")
        return str(out)

    except Exception as exc:
        logger.warning(f"Google GenAI image failed ({exc}); falling back to Matplotlib chart")
        return _fallback_chart(config)


def _fallback_chart(config: dict) -> str:
    return generate_chart({
        "title": config.get("title", "Topic Overview"),
        "chart_type": "bar",
        "labels": ["Research", "Analysis", "Insights", "Action"],
        "values": [85, 72, 91, 68],
        "ylabel": "Score",
    })


def _render_viral_card(config: dict) -> str:
    import textwrap
    from matplotlib.patches import FancyBboxPatch, Circle

    title = config.get("title", "Career Signal")
    subtitle = config.get("subtitle", "")
    tag = config.get("tag", "VIRAL")
    bullets = (config.get("bullets") or [])[:3]

    fig = plt.figure(figsize=(8, 8))
    fig.patch.set_facecolor("#fff8ef")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.add_patch(Circle((0.16, 0.84), 0.12, transform=ax.transAxes, color="#ffd86b", alpha=0.85))
    ax.add_patch(Circle((0.88, 0.16), 0.16, transform=ax.transAxes, color="#b8e0ff", alpha=0.65))
    ax.add_patch(Circle((0.82, 0.82), 0.08, transform=ax.transAxes, color="#ff8b6a", alpha=0.55))

    ax.add_patch(FancyBboxPatch(
        (0.07, 0.86), 0.2, 0.055,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        transform=ax.transAxes,
        facecolor="#111111",
        edgecolor="none",
    ))
    ax.text(
        0.17, 0.888, tag.upper(),
        ha="center", va="center",
        color="#ffffff", fontsize=11, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    ax.text(
        0.07, 0.75, textwrap.fill(title, width=16),
        ha="left", va="top",
        color="#111111", fontsize=30, fontweight="bold",
        linespacing=1.05,
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    if subtitle:
        ax.text(
            0.07, 0.59, textwrap.fill(subtitle, width=34),
            ha="left", va="top",
            color="#4f5560", fontsize=13.5,
            linespacing=1.35,
            transform=ax.transAxes, fontfamily="DejaVu Sans",
        )

    card_y = 0.21 if bullets else 0.27
    card_h = 0.3 if bullets else 0.22
    ax.add_patch(FancyBboxPatch(
        (0.07, card_y), 0.86, card_h,
        boxstyle="round,pad=0.018,rounding_size=0.04",
        transform=ax.transAxes,
        facecolor="#ffffff",
        edgecolor="#ecd8c8",
        linewidth=1.2,
    ))

    if bullets:
        for i, bullet in enumerate(bullets):
            y = card_y + card_h - 0.075 - i * 0.082
            ax.add_patch(Circle((0.11, y + 0.005), 0.009, transform=ax.transAxes, color="#1877F2"))
            ax.text(
                0.135, y, textwrap.fill(bullet, width=28),
                ha="left", va="center",
                color="#16202a", fontsize=15, fontweight="bold",
                linespacing=1.2,
                transform=ax.transAxes, fontfamily="DejaVu Sans",
            )
    else:
        ax.text(
            0.11, card_y + card_h / 2, "Fresh angle. Clear takeaway.",
            ha="left", va="center",
            color="#16202a", fontsize=16, fontweight="bold",
            transform=ax.transAxes, fontfamily="DejaVu Sans",
        )

    ax.text(
        0.07, 0.08, "Surrounded by Data",
        ha="left", va="center",
        color="#111111", fontsize=14, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )
    ax.text(
        0.93, 0.08, "Bangla-first data/AI",
        ha="right", va="center",
        color="#6d737d", fontsize=11.5,
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    out = _VISUALS_DIR / f"viral_{_ts()}.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor(), pad_inches=0.2)
    plt.close()
    logger.info(f"Viral image saved → {out}")
    return str(out)


# ── news digest cover image ───────────────────────────────────────────────────

def generate_news_image(headlines: list | None = None) -> str:
    """Create a polished square news cover with strong hierarchy and 3 headline cards."""
    import textwrap
    from datetime import date
    from matplotlib.patches import FancyBboxPatch, Circle

    fig = plt.figure(figsize=(8, 8))
    fig.patch.set_facecolor("#07111f")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Subtle layered background
    gradient = [[0.0, 0.2], [0.35, 1.0]]
    ax.imshow(
        gradient,
        extent=[0, 1, 0, 1],
        origin="lower",
        cmap="Blues",
        alpha=0.23,
        aspect="auto",
    )
    ax.add_patch(Circle((0.88, 0.88), 0.18, transform=ax.transAxes, color="#1877F2", alpha=0.09))
    ax.add_patch(Circle((0.12, 0.12), 0.14, transform=ax.transAxes, color="#42B72A", alpha=0.06))

    # Top tag
    ax.add_patch(FancyBboxPatch(
        (0.07, 0.88), 0.2, 0.05,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        transform=ax.transAxes,
        facecolor="#1877F2",
        edgecolor="none",
        alpha=0.95,
    ))
    ax.text(
        0.17, 0.905, "DAILY BRIEF",
        ha="center", va="center",
        color="#ffffff", fontsize=11, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    # Main title block
    ax.text(
        0.07, 0.81, "Tech News",
        ha="left", va="center",
        color="#ffffff", fontsize=31, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )
    ax.text(
        0.07, 0.74, "Digest",
        ha="left", va="center",
        color="#8ec5ff", fontsize=31, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )
    ax.text(
        0.07, 0.68, "Top AI and tech updates at a glance",
        ha="left", va="center",
        color="#a9b7c6", fontsize=12.5,
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    # Date pill
    ax.add_patch(FancyBboxPatch(
        (0.62, 0.76), 0.28, 0.07,
        boxstyle="round,pad=0.015,rounding_size=0.025",
        transform=ax.transAxes,
        facecolor="#101c2d",
        edgecolor="#23415f",
        linewidth=1.2,
    ))
    ax.text(
        0.76, 0.795, date.today().strftime("%B %d, %Y"),
        ha="center", va="center",
        color="#d8e7f7", fontsize=13, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    card_specs = [
        (0.07, 0.50, 0.86, 0.12),
        (0.07, 0.34, 0.86, 0.12),
        (0.07, 0.18, 0.86, 0.12),
    ]
    fallback = ["AI market moves fast", "Platforms keep shipping", "Builders need context"]
    display_headlines = (headlines or fallback)[:3]

    for i, (headline, (x, y, w, h)) in enumerate(zip(display_headlines, card_specs), start=1):
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            transform=ax.transAxes,
            facecolor="#0d1726",
            edgecolor="#1f324a",
            linewidth=1.3,
            alpha=0.98,
        ))
        ax.add_patch(FancyBboxPatch(
            (x + 0.018, y + 0.024), 0.065, h - 0.048,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            transform=ax.transAxes,
            facecolor="#1877F2" if i == 1 else ("#42B72A" if i == 2 else "#F7B928"),
            edgecolor="none",
            alpha=0.95,
        ))
        ax.text(
            x + 0.05, y + h / 2, f"{i}",
            ha="center", va="center",
            color="#ffffff", fontsize=18, fontweight="bold",
            transform=ax.transAxes, fontfamily="DejaVu Sans",
        )
        wrapped = textwrap.fill(headline, width=26)
        ax.text(
            x + 0.105, y + h / 2, wrapped,
            ha="left", va="center",
            color="#ffffff", fontsize=16, fontweight="bold",
            linespacing=1.3,
            transform=ax.transAxes, fontfamily="DejaVu Sans",
        )

    ax.plot([0.07, 0.93], [0.12, 0.12], color="#20364f", linewidth=1.1, transform=ax.transAxes)
    ax.text(
        0.07, 0.07, "Surrounded by Data",
        ha="left", va="center",
        color="#d7e4f3", fontsize=14, fontweight="bold",
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )
    ax.text(
        0.93, 0.07, "AI • Data • Tech",
        ha="right", va="center",
        color="#6f849b", fontsize=11.5,
        transform=ax.transAxes, fontfamily="DejaVu Sans",
    )

    out = _VISUALS_DIR / f"news_{_ts()}.png"
    plt.savefig(
        out, dpi=160, bbox_inches="tight",
        facecolor="#07111f", pad_inches=0.22,
    )
    plt.close()
    logger.info(f"News image saved → {out}")
    return str(out)


# ── viral social image ────────────────────────────────────────────────────────

def generate_viral_image(config: dict) -> str:
    """Generate a viral-post image using AI illustration when available, else a polished local card."""
    if GOOGLE_API_KEY and config.get("prompt"):
        try:
            out = _VISUALS_DIR / f"viral_{_ts()}.png"
            _generate_google_image(config["prompt"], out, aspect_ratio="1:1")
            logger.info(f"Viral AI image saved → {out}")
            return str(out)
        except Exception as exc:
            logger.warning(f"Viral AI image failed ({exc}); falling back to topic card")

    return _render_viral_card(config)


# ── motivational quote image ──────────────────────────────────────────────────

def generate_quote_image(paragraphs: list[str]) -> str:
    """
    Render a motivational quote as bold white text on a pure black background.
    Large punchy text; branded page name with blue verified dot at the bottom.
    """
    import textwrap

    # Wrap each paragraph at ~28 chars — forces short punchy lines
    wrapped_blocks: list[str] = []
    for para in paragraphs:
        lines = []
        for raw_line in para.split("\n"):
            lines.append(textwrap.fill(raw_line.strip(), width=28))
        wrapped_blocks.append("\n".join(lines))

    full_text = "\n\n".join(wrapped_blocks)
    total_lines = sum(b.count("\n") + 1 for b in wrapped_blocks) + len(wrapped_blocks) - 1

    # Scale height to content — portrait, phone-friendly
    fig_h = max(8.0, total_lines * 0.72 + 5.5)
    fig = plt.figure(figsize=(8, fig_h))
    fig.patch.set_facecolor("#000000")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("#000000")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Thin top accent line
    ax.axhline(y=0.96, xmin=0.06, xmax=0.94, color="#1877F2", linewidth=2, alpha=0.6)

    # Main quote text — large, left-padded, vertically centred
    ax.text(
        0.07, 0.58,
        full_text,
        ha="left",
        va="center",
        color="#ffffff",
        fontsize=34,
        fontweight="bold",
        linespacing=1.65,
        multialignment="left",
        transform=ax.transAxes,
        fontfamily="DejaVu Sans",
    )

    # Bottom separator line
    ax.axhline(y=0.10, xmin=0.06, xmax=0.94, color="#222222", linewidth=1.5)

    # Blue verified dot
    ax.text(
        0.07, 0.055,
        "●",
        ha="left",
        va="center",
        color="#1877F2",
        fontsize=18,
        fontweight="bold",
        transform=ax.transAxes,
        fontfamily="DejaVu Sans",
    )

    # Page name — prominent, right of dot
    ax.text(
        0.135, 0.055,
        "Surrounded by Data",
        ha="left",
        va="center",
        color="#dddddd",
        fontsize=18,
        fontweight="bold",
        transform=ax.transAxes,
        fontfamily="DejaVu Sans",
    )

    out = _VISUALS_DIR / f"quote_{_ts()}.png"
    plt.savefig(
        out, dpi=150, bbox_inches="tight",
        facecolor="#000000", pad_inches=0.5,
    )
    plt.close()
    logger.info(f"Quote image saved → {out}")
    return str(out)


# ── public entry ──────────────────────────────────────────────────────────────

def generate_visual(visual_type: str, config: dict) -> str:
    """Dispatch to the correct generator. Returns path to the saved image file."""
    if visual_type == "chart":
        return generate_chart(config)
    if visual_type == "flowchart":
        return generate_flowchart(config)
    if visual_type == "image":
        return generate_ai_image(config)
    if visual_type == "viral":
        return generate_viral_image(config)
    if visual_type == "quote":
        return generate_quote_image(config.get("paragraphs", []))
    if visual_type == "news":
        return generate_news_image(config.get("headlines"))
    raise ValueError(f"Unknown visual_type: {visual_type!r}")
