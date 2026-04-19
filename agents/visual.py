"""
Visual generation module.

Priority order per visual_type:
  chart      → Matplotlib (free, local)
  flowchart  → mermaid.ink API (free, no auth)
  image      → Google Imagen 3 via google-generativeai, falls back to Matplotlib chart
"""

import base64
import os
from datetime import datetime
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

def generate_ai_image(config: dict) -> str:
    prompt = config.get("prompt", "A professional technology concept illustration, clean and modern")

    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set — falling back to Matplotlib chart")
        return _fallback_chart(config)

    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)

        model = genai.ImageGenerationModel("imagen-3.0-generate-001")
        result = model.generate_images(
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_some",
            person_generation="allow_adult",
        )
        out = _VISUALS_DIR / f"image_{_ts()}.png"
        result.images[0].save(str(out))
        logger.info(f"AI image saved → {out}")
        return str(out)

    except Exception as exc:
        logger.warning(f"Google Imagen failed ({exc}); falling back to Matplotlib chart")
        return _fallback_chart(config)


def _fallback_chart(config: dict) -> str:
    return generate_chart({
        "title": config.get("title", "Topic Overview"),
        "chart_type": "bar",
        "labels": ["Research", "Analysis", "Insights", "Action"],
        "values": [85, 72, 91, 68],
        "ylabel": "Score",
    })


# ── public entry ──────────────────────────────────────────────────────────────

def generate_visual(visual_type: str, config: dict) -> str:
    """Dispatch to the correct generator. Returns path to the saved image file."""
    if visual_type == "chart":
        return generate_chart(config)
    if visual_type == "flowchart":
        return generate_flowchart(config)
    if visual_type == "image":
        return generate_ai_image(config)
    raise ValueError(f"Unknown visual_type: {visual_type!r}")
