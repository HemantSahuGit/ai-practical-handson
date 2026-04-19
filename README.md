# AI practical hands-on

Boilerplate for a **natural-language data agent** (API-first; test with Postman, curl, or FastAPI docs):

- **FastAPI** exposes `POST /api/chat` and `GET /api/sessions/{id}/messages`.
- **OpenAI** powers routing and answers via function tools (`answer_from_context`, `run_readonly_sql`).
- **ChromaDB** (embedded, on-disk) stores schema documentation chunks retrieved per question.
- **PostgreSQL** holds demo fact data and durable chat history.

## Security notes

- Keep `OPENAI_API_KEY` on the server only (`.env`, not committed).
- The agent only runs SQL that passes lightweight `SELECT` / `WITH` checks. For real workloads, also use a **read-only database role** and tight network rules.
- Generated SQL can still be wrong or expensive; review before widening access.

## Prerequisites

- Python 3.12+ and [uv](https://github.com/astral-sh/uv)
- Docker (for Postgres)

## Quick start

1. **Start Postgres**

   ```bash
   docker compose up -d
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Set `OPENAI_API_KEY` and confirm `DATABASE_URL` matches `docker-compose.yml` (default: `postgresql+asyncpg://app:app@127.0.0.1:5432/app`).

3. **Install Python dependencies**

   ```bash
   uv sync
   ```

4. **Seed Chroma with schema docs** (requires `OPENAI_API_KEY`)

   ```bash
   uv run python scripts/seed_chroma.py
   ```

5. **Run the API**

   ```bash
   uv run uvicorn app.main:app --reload
   ```

6. **Try it** — open `http://127.0.0.1:8000/docs` (Swagger UI) or use **Postman**:
   - `POST http://127.0.0.1:8000/api/chat`  
     Body (JSON): `{ "session_id": null, "message": "What is sales_fact?" }`  
     Use the returned `session_id` on later calls to continue the thread.
   - `GET http://127.0.0.1:8000/api/sessions/{session_id}/messages` to inspect history.

## API

- `GET /health` — liveness.
- `POST /api/chat` — body `{ "session_id": "<uuid> | null", "message": "..." }`. Omit `session_id` to start a new session.
- `GET /api/sessions/{session_id}/messages` — chronological messages for debugging.

## Project layout

- [`app/`](app/) — FastAPI application (config, DB, Chroma wrapper, agent, routes).
- [`scripts/init_pg.sql`](scripts/init_pg.sql) — demo `sales_fact` table + sample rows (loaded on first Postgres init).
- [`scripts/seed_chroma.py`](scripts/seed_chroma.py) — uploads example schema documentation into Chroma.

## Environment variables

See [`.env.example`](.env.example). Set `CORS_ORIGINS` to a comma-separated list only if you call the API from a browser on another origin; Postman does not need CORS.
