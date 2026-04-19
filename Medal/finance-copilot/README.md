# Finance Copilot (MVP)

AI-assisted personal finance workspace: ingest CSV bank exports, auto-categorize with rules, surface insights, and answer questions through a copilot that maps **natural language → structured intent → deterministic queries** (models never touch SQL directly).

## Troubleshooting (upload / copilot)

- **Copilot field not responding:** Hard-refresh the dashboard (`Ctrl+F5`). Older builds loaded Chart.js with `defer`; if the CDN was blocked, the dashboard script never ran so nothing was wired up. Current templates load scripts at the bottom of the page and use safe chart creation.
- **Upload fails after deploy:** Use **root-relative API paths** with your mount prefix. Templates set `window.__API_ROOT__` from `request.script_root` so `/api/upload` becomes `/your-prefix/api/upload` when the app is mounted under a subpath. If you reverse-proxy only `/api` to Flask, align `SCRIPT_NAME` / proxy headers with your Flask docs.
- **SQLite errors on cloud:** The DB file must be on a **writable** path. Set `DATABASE_PATH` to a persistent volume. With Gunicorn, use **one worker** for SQLite (the included `Dockerfile` does) or switch to Postgres.

## Quick start

```bash
cd finance-copilot
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`, upload `data/sample.csv` (or use **Load sample CSV**), then open the dashboard.

### Environment

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Optional; enables GPT-4o-mini for intent JSON |
| `GEMINI_API_KEY` | Optional; set `LLM_PROVIDER=gemini` to use Gemini |
| `DATABASE_PATH` | SQLite file location (default `data/copilot.db`) |
| `SECRET_KEY` | Flask secret |

Without LLM keys, a **rule-based intent parser** still powers the copilot.

### Docker

```bash
cd finance-copilot
docker build -t finance-copilot .
docker run --rm -p 5000:5000 finance-copilot
```

## API map

- `POST /api/upload` — multipart field `file` (CSV). Form field `replace=false` to append instead of replacing rows.
- `GET /api/sample-csv` — bundled sample transactions.
- `GET /api/dashboard/summary` — income, expense, net, savings rate.
- `GET /api/dashboard/category-breakdown` — category totals for pie chart.
- `GET /api/dashboard/monthly-trend` — monthly income, expense, savings.
- `GET /api/dashboard/insights` — text insight bundle.
- `GET /api/dashboard/health-score` — 0–100 score + headline + component breakdown.
- `GET /api/dashboard/subscriptions` — recurring merchants (same amount, ~monthly cadence; excludes rent/utilities by default).
- `GET /api/dashboard/anomalies` — expenses above 2× their category average.
- `POST /api/copilot/query` — JSON `{"query": "..."}` → `{ insight, data, chart, intent }`.

## Architecture

```
Browser (dashboard + chat)
    ↓ REST
Flask blueprints (/api/upload, /api/dashboard, /api/copilot)
    ↓
Services: parser → categorizer → SQLite
          insights (pandas)
          nlp_engine (LLM or rules) → query_engine (pandas/SQL) → JSON chart payloads
```

## MVP checklist

- CSV upload + pandas normalization (`date`, `description`, `amount`, inferred `type`).
- Rule-based categories (Swiggy/Zomato → Food, Uber/Ola → Travel, etc.).
- SQLite `transactions` table with `user_id` (default `1` for demo).
- Dashboard charts (Chart.js) + ≥3 narrative insights.
- Copilot responses with `{insight, data, chart}` for common intents.

## Project layout

See repository `finance-copilot/` for `app.py`, `routes/`, `services/`, `models/`, `templates/`, `static/`, and `data/sample.csv`.
