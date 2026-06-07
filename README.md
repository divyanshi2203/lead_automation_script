# Lead Automation

A small system that takes inbound leads, uses an LLM to classify them as
**Hot / Warm / Cold** and draft a reply, stores them, and shows them in a
dashboard a non-technical user can operate.

## Architecture

```
   sample_leads.csv / POST /lead
                |
                v
   +-------------------------+        +------------------+
   |   Python backend        |  LLM   |  Claude API      |
   |   (FastAPI)             | <----> |  (rule fallback) |
   |   stores leads.json     |        +------------------+
   +-------------------------+
        ^                  ^
        | GET /leads       | GET /leads (hourly)
        |                  |
   +---------+        +-------------------+
   | Next.js |        | n8n automation    |
   | table   |        | -> Slack digest   |
   +---------+        +-------------------+
```

Three parts that connect over HTTP: the **backend** is the source of truth,
the **frontend** reads/writes it for humans, and the **automation** reads it
on a schedule for notifications.

## Run it (one command per part)

**1. Backend** (http://localhost:8000)

```bash
cd backend && pip install -r requirements.txt && uvicorn main:app --port 8000
```

The 10 sample leads load automatically on first start.
To use Claude instead of the keyword fallback: `export ANTHROPIC_API_KEY=sk-...`

**2. Frontend** (http://localhost:3000)

```bash
cd frontend && npm install && npm run dev
```

**3. Automation** — import `automation/n8n-hot-leads-digest.json` into n8n,
add your Slack webhook URL, and activate.

## Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `/lead` | Accept + classify + store a lead |
| GET | `/leads` | Return all leads |
| POST | `/classify` | Classify a raw message string |
| POST | `/leads/{id}/contacted` | Mark a lead as contacted |

## Tools used and why

- **FastAPI** — fast to write, validates request bodies, auto docs at `/docs`.
- **JSON file storage** — simplest queryable store; no DB setup needed.
- **Anthropic Claude** for classification, with a keyword fallback so the app
  runs even without an API key.
- **Next.js (App Router)** — required stack; one page, plain CSS, no build config.
- **n8n** — free/open-source, exports the flow as JSON.

## Tradeoffs / what I'd improve with more time

- JSON file is fine for 10 leads but not concurrent writes — I'd move to SQLite.
- Classification prompt is basic; I'd add few-shot examples and confidence scores.
- No pagination/search on the dashboard; fine at this scale.
- The LLM reply isn't editable in the UI yet — I'd add an inline edit + send.
