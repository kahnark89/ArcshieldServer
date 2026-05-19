# arcshield-corpus — Project Memory

**Owner:** Kahn Capps, Capps Family Enterprises  
**Deployment:** Hollowell Industries PPVC Line 1 (local plant LAN, no cloud)  
**Companion app:** ArcShieldDAQ (Android, separate repo)

## What this is

Server half of the ArcShield two-unit system. Stores the CIAER+ event corpus, serves a RAG endpoint for the Android AI Twin, and hosts the React web dashboard for event review and threshold management.

## Stack

- **API:** FastAPI + uvicorn (Python 3.11+, async throughout)
- **DB:** PostgreSQL 16 + TimescaleDB + pgvector
- **ORM:** SQLAlchemy 2.0 async + Alembic migrations
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2` (384-dim)
- **Scheduler:** APScheduler (hourly threshold recalculation)
- **Dashboard:** React + Vite (served from `/dashboard` by FastAPI StaticFiles)

## Key conventions

- All Python code is async. No blocking calls in request handlers.
- Pydantic v2: use `model_validate`, not `parse_obj`.
- SQLAlchemy 2.0 async with `AsyncSession`. Never `.sync_session`.
- Every schema change goes through Alembic — never `ALTER TABLE` in prod.
- API key auth via `X-API-Key` header for all non-dashboard routes.
- Dashboard routes and `/health` / `/docs` are unauthenticated.

## Project layout

```
app/
  main.py          FastAPI app + middleware + lifespan
  config.py        pydantic-settings Settings (reads .env)
  database.py      engine + AsyncSessionLocal + get_db()
  models/          SQLAlchemy ORM: event.py, sensor_stream.py, threshold.py
  schemas/         Pydantic: ciaer_event.py (CIAER+ contract), api_responses.py
  routers/         events.py, twin.py, config.py, media.py
  services/        embedding.py, rag.py, threshold.py
  tasks/           threshold_recalc.py (APScheduler)
alembic/           DB migrations
dashboard/         React + Vite SPA (build → dist/, served at /dashboard)
tests/             pytest + httpx AsyncClient
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /events | Ingest CIAER+ event from Android SyncWorker |
| GET | /events | List events (paginated, filterable) |
| GET | /events/{id} | Full event JSON |
| PATCH | /events/{id}/feedback | Set TP/FP label |
| GET | /twin/query | RAG: top-N similar past events |
| GET | /config/threshold | Current threshold for operator |
| PATCH | /config/threshold | Manual override [0.55, 0.80] |
| GET | /config/threshold/history | Threshold adjustment log |
| GET | /media/frames/{filename} | Serve pre-trigger frame |

## Running locally

```bash
cp .env.example .env
docker compose up --build          # starts db + api
# or for dev (needs local postgres with timescaledb + pgvector):
pip install -e .[dev]
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest tests/
```

## Dynamic threshold logic (detection-spec §7.5)

- Every hour, count TP/FP events per operator in the last 60 min
- If hourly_FP > 2: threshold += 0.03
- If hourly_FP < 0.5 AND hourly_TP > 1: threshold -= 0.03
- Clamp to [0.55, 0.80]
- Android app reads the adjusted threshold on shift start via GET /config/threshold

## RAG pipeline

Phase 1 (< 200 events): pure retrieval with pgvector cosine similarity.  
Phase 2 (~200 validated events): LoRA fine-tuning — endpoint shape unchanged.

## Android integration points

| Android component | Endpoint |
|---|---|
| SyncWorker → LocalServerSink | POST /events |
| TwinClient | GET /twin/query |
| FusionEngine (TODO) | GET /config/threshold |
| Result phase (TODO) | PATCH /events/{id}/feedback |
