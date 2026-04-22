# Surrounded by Data — Facebook Auto-Poster

An autonomous AI agent that researches, writes, and posts content to the **Surrounded by Data** Facebook page three times a day — fully hands-free.

---

## What It Does

| Time (BD) | Post Type | Description |
|-----------|-----------|-------------|
| **10:00 AM** | Tech News Digest | Searches the web via Tavily, picks the 3 most important tech/AI stories of the day, writes an engaging English post |
| **08:00 PM** | Bengali Tutorial | Picks a fresh data science / ML / AI / database topic (never repeats), writes a beginner-friendly lesson in Bengali, generates a topic-appropriate visual (bar chart, line chart, pie, scatter, histogram, or flowchart) |
| **11:00 PM** | Motivational Quote | Generates an original career/life/skill quote, renders it as bold white text on a pure black image in the style of Jeff Moore quote posts, watermarked with the page name |

---

## Architecture

```
Tavily API  ──►  researcher.py  ──►  writer.py (Claude Sonnet)
                                          │
                              ┌───────────┼───────────────┐
                              │           │               │
                         news_digest  tutorial_bn    motive_quote
                              │           │               │
                              │      visual.py ◄──────────┘
                              │      (chart / flowchart / quote image)
                              │           │
                              └─────►  facebook.py  ──►  Facebook Graph API
```

**Stack:**

| Layer | Tool | Cost |
|-------|------|------|
| Research | Tavily AI (free tier — 1,000 searches/month) | $0 |
| AI Writing | Claude Sonnet (`claude-sonnet-4-6`) | ~$0.22/month |
| Charts & Graphs | Matplotlib (local, Python) | $0 |
| Flowcharts | mermaid.ink API (free, no auth) | $0 |
| AI Images | Google Imagen 4 (`imagen-4.0-generate-001`, optional if `GOOGLE_API_KEY` set) | ~$0.02/image |
| FB Posting | Facebook Graph API v19.0 | $0 |
| Scheduling | APScheduler with `Asia/Dhaka` timezone | $0 |
| Hosting | Railway free tier (or any VPS) | $0–$5/month |

**Estimated total: $0.22 – $1.50 / month**

---

## File Structure

```
automatic_fb_page_posting/
├── main.py                    # Entry point — scheduler + slot dispatch
├── config.py                  # Loads and validates .env variables
├── requirements.txt
├── .env.example               # Template — copy to .env and fill in keys
├── Procfile                   # Railway deployment
├── railway.toml               # Railway build config
│
├── agents/
│   ├── researcher.py          # Tavily web search → research summary
│   ├── writer.py              # Claude Sonnet — 3 content generators
│   ├── visual.py              # Matplotlib + mermaid.ink + quote image renderer
│   └── topic_tracker.py       # Persists posted tutorial topics → data/posted_topics.json
│
├── poster/
│   └── facebook.py            # Facebook Graph API: text post + photo post
│
├── utils/
│   └── logger.py              # Dual console + daily file logging
│
├── data/
│   └── posted_topics.json     # Auto-created — tracks used tutorial topics
│
├── visuals/                   # Temp image files (auto-deleted after upload)
└── logs/                      # Daily log files (fb_poster_YYYYMMDD.log)
```

---

## Setup

### 1. Clone & install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Fill in the values:

```env
TAVILY_API_KEY=tvly-...          # https://tavily.com
ANTHROPIC_API_KEY=sk-ant-...     # https://console.anthropic.com
GOOGLE_API_KEY=AIza...           # Optional — for AI-generated images
FB_PAGE_ACCESS_TOKEN=EAA...      # Facebook long-lived Page Access Token
FB_PAGE_ID=61572022241624        # Your Facebook Page numeric ID

POST_TIMES=10:00,20:00,23:00     # Bangladesh times (slot 1, 2, 3)
TIMEZONE=Asia/Dhaka
```

If AI image generation fails with `cannot import name 'genai' from 'google'`, reinstall the newer SDK in the same environment that runs the app:

```bash
py -m pip uninstall -y google-generativeai google-ai-generativelanguage google
py -m pip install --upgrade pip
py -m pip install --no-cache-dir google-genai
```

### 3. Get a Facebook Page Access Token

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create an app → add **Facebook Login** + **Pages API** products
3. Generate a short-lived User Token with `pages_manage_posts` + `pages_read_engagement`
4. Exchange for a **long-lived token** (valid ~60 days):
   ```
   GET https://graph.facebook.com/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={APP_ID}
     &client_secret={APP_SECRET}
     &fb_exchange_token={SHORT_LIVED_TOKEN}
   ```
5. Use the token to get your **Page Access Token**:
   ```
   GET https://graph.facebook.com/me/accounts?access_token={LONG_LIVED_USER_TOKEN}
   ```

> **Reminder:** Long-lived tokens expire in ~60 days. Rotate before expiry to avoid missed posts.

---

## Usage

### Run the full scheduler (production)

```bash
python main.py
```

### Test individual slots without waiting for the schedule

```bash
python main.py --test 0    # Tech news digest (10 AM slot)
python main.py --test v1   # viral content mid-day
python main.py --test 1    # Bengali tutorial with visual (8 PM slot)
python main.py --test v2   # viral content late night
```

---

## Deploying to Railway

1. Push this repo to GitHub
2. Create a new Railway project → connect the repo
3. Add all `.env` keys as **environment variables** in Railway dashboard
4. Railway reads `railway.toml` and runs `python main.py` as a persistent worker

The worker stays alive 24/7 and fires the scheduler jobs at the configured times.

---

## How the Bengali Tutorial Topic Tracker Works

Every time the 8 PM slot runs, `topic_tracker.py`:
1. Reads `data/posted_topics.json` — the list of already-covered topics
2. Passes it to Claude in the prompt ("Do NOT repeat these")
3. After a successful post, saves the new topic to the JSON file

This ensures every tutorial is on a unique topic. The file is human-editable — you can remove a topic from the list if you want it covered again.

---

## Quote Image Style

The 11 PM motivational quote is rendered locally (no external API) using Matplotlib:

- Pure black `#000000` background
- Bold white text, 27pt DejaVu Sans
- Short punchy paragraphs separated by blank lines (inspired by Jeff Moore / stoic quote pages)
- `Surrounded by Data` watermark in italic grey at the bottom-right

---

## Customisation

| What to change | Where |
|----------------|-------|
| Posting times | `POST_TIMES` in `.env` |
| Timezone | `TIMEZONE` in `.env` |
| News research query | `run_news_digest()` in `main.py` |
| Tutorial domains | `_TUTORIAL_PROMPT` in `agents/writer.py` |
| Quote themes | `_QUOTE_PROMPT` in `agents/writer.py` |
| Visual style / colours | `agents/visual.py` |
| Page watermark name | `generate_quote_image()` in `agents/visual.py` |
