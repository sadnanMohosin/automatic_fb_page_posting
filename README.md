# Surrounded by Data - Facebook Auto-Poster

An autonomous content system that researches, writes, visualizes, and publishes posts to the **Surrounded by Data** Facebook page on a daily Bangladesh schedule.

---

## What It Does

| Time (BD) | Post Type | Description |
|-----------|-----------|-------------|
| **10:00 AM** | Tech News Digest | Uses Tavily research to find important tech and AI updates, then writes a Bengali digest with a branded news cover image |
| **08:00 PM** | Bengali Tutorial | Plans a family-aware tutorial topic with rotating difficulty, researches it via Tavily, writes a segmented Bengali lesson, and generates a teaching visual such as a chart, flowchart, table, matrix, comparison card, or architecture diagram |
| **11:00 PM** | Motivational Quote | Quote renderer exists, but the scheduled slot is currently disabled in `main.py` |

---

## Tutorial Upgrade

The tutorial slot is no longer a one-shot beginner explainer.

It now works like this:

1. `plan_tutorial_bengali()` picks a fresh topic inside a rotating tutorial family and difficulty level.
2. `research_tutorial_topic()` pulls supporting examples, mistakes, and tradeoffs for that exact topic.
3. `generate_tutorial_bengali()` writes a structured Bengali lesson with this flow:
   hook -> why it matters -> key terms -> worked example -> common mistake -> mini challenge -> takeaway
4. `generate_visual()` renders the most useful visual for that lesson.

Difficulty rotates across the week:

- `foundation`
- `intermediate`
- `advanced`

Topic families include:

- SQL analytics
- data modeling
- ML evaluation
- feature engineering
- experimentation and analytics
- data pipelines
- LLM systems
- statistics for decision making

This keeps tutorials sharper, less repetitive, and more useful for readers who are moving beyond basics.

---

## Architecture

```text
Tavily API  -->  researcher.py  -->  writer.py (Claude Sonnet)
                                        |
                            +-----------+-------------+
                            |           |             |
                        news_digest  tutorial_bn   quote/viral
                            |           |             |
                            |       visual.py <-------+
                            |   (chart / flowchart / table /
                            |    matrix / comparison / architecture /
                            |    quote image / AI image)
                            |           |
                            +-------> facebook.py --> Facebook Graph API
```

---

## Stack

| Layer | Tool |
|-------|------|
| Research | Tavily |
| Writing | Claude Sonnet (`claude-sonnet-4-6`) |
| Local visuals | Matplotlib |
| Diagram rendering | mermaid.ink |
| Optional AI images | Google Imagen 4 (`imagen-4.0-generate-001`) |
| Scheduling | APScheduler |
| Posting | Facebook Graph API |

---

## File Structure

```text
automatic_fb_page_posting/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
├── Procfile
├── railway.toml
├── agents/
│   ├── researcher.py
│   ├── writer.py
│   ├── visual.py
│   └── topic_tracker.py
├── poster/
│   └── facebook.py
├── utils/
│   └── logger.py
├── data/
│   ├── posted_topics.json
│   └── tutorial_history.json
├── visuals/
└── logs/
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```bash
cp .env.example .env
```

Fill in the values:

```env
TAVILY_API_KEY=tvly-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...        # Optional
FB_PAGE_ACCESS_TOKEN=EAA...
FB_PAGE_ID=61572022241624

POST_TIMES=10:00,20:00,23:00
TIMEZONE=Asia/Dhaka
```

### 3. Google image SDK troubleshooting

If AI image generation fails with `cannot import name 'genai' from 'google'`, reinstall the newer SDK in the same Python environment that runs the app:

```bash
python -m pip uninstall -y google-generativeai google-ai-generativelanguage google
python -m pip install --upgrade pip
python -m pip install --no-cache-dir google-genai
python -m pip install -r requirements.txt
```

If the Google REST call returns `403` with a leaked-key message, the API key has been flagged by Google and must be replaced with a new key.

### 4. Facebook Page Access Token

1. Create a Facebook app at `developers.facebook.com`.
2. Add the needed Pages permissions.
3. Generate a user token.
4. Exchange it for a long-lived token.
5. Fetch the Page access token and place it in `.env`.

---

## Usage

Run the full scheduler:

```bash
python main.py
```

Run individual jobs:

```bash
python main.py --test 0
python main.py --test 1
python main.py --test v1
python main.py --test v2
```

Targets:

- `0` = news digest
- `1` = Bengali tutorial
- `v1` = viral day content
- `v2` = viral night content

---

## Bengali Tutorial Flow

Every tutorial post now stores richer history after publishing.

`topic_tracker.py` writes:

- `data/tutorial_history.json` with topic, family, difficulty, learning goal, research query, and timestamp
- `data/posted_topics.json` as a simple topic-name list for backward compatibility

This helps avoid:

- exact topic repeats
- staying stuck on only beginner topics
- overusing the same topic family too frequently

---

## Supported Tutorial Visuals

The tutorial writer can now choose from:

- `chart`
- `flowchart`
- `table`
- `matrix`
- `comparison`
- `architecture`

Recommended use:

- `table` for SQL outputs, before/after rows, compact feature comparisons
- `matrix` for confusion matrices, decision grids, or cell-by-cell metric views
- `comparison` for wrong way vs right way, precision vs recall, star vs snowflake, etc.
- `architecture` for ETL, RAG, and system pipeline explanations

---

## Deploying to Railway

1. Push the repo to GitHub.
2. Create a Railway project and connect the repo.
3. Add all environment variables in the Railway dashboard.
4. Railway runs `python main.py` as a long-running worker.

---

## Customisation

| What to change | Where |
|----------------|-------|
| Posting times | `.env` -> `POST_TIMES` |
| Timezone | `.env` -> `TIMEZONE` |
| News research query | `run_news_digest()` in `main.py` |
| Tutorial family rotation and difficulty schedule | `agents/writer.py` |
| Tutorial research prompt | `agents/researcher.py` |
| Tutorial visual styles | `agents/visual.py` |
| Topic history behavior | `agents/topic_tracker.py` |
| Quote rendering | `generate_quote_image()` in `agents/visual.py` |
