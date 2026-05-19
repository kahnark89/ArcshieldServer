# arcshield-corpus — Local Setup Guide

Running the server on a laptop for Hollowell Industries PPVC Line 1.

---

## Prerequisites

### Path A — Docker Compose (recommended)

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose plugin (Linux)
- 4 GB RAM available to Docker

### Path B — Local dev (no Docker for the API)

- Python 3.11+
- Node 20+
- Docker Desktop (for the database only) **or** a local PostgreSQL 16 instance with TimescaleDB and pgvector extensions

---

## Path A: Docker Compose

Everything runs inside containers. Recommended for running on the plant laptop as a stable local server.

### 1. Clone and configure

```bash
git clone https://github.com/kahnark89/arcshieldserver.git
cd arcshieldserver
cp .env.example .env
```

Open `.env` and set a real API key:

```
API_KEY=your-secret-key-here
```

The Android app must use this same key. Leave all other values as-is if running locally.

### 2. Build and start

```bash
docker compose up --build
```

First run takes a few minutes — it downloads the TimescaleDB image, builds the Python image, installs sentence-transformers (~500 MB including the `all-MiniLM-L6-v2` model), and builds the React dashboard.

On subsequent runs:

```bash
docker compose up
```

### 3. Verify

```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Current threshold for operator kahn (requires API key)
curl -H "X-API-Key: your-secret-key-here" \
  "http://localhost:8000/config/threshold?operator_id=kahn"

# RAG query
curl -H "X-API-Key: your-secret-key-here" \
  "http://localhost:8000/twin/query?cause=pressure+spike&limit=3"
```

### 4. Open the dashboard

Navigate to `http://localhost:8000/dashboard` in a browser on the same machine.

### 5. Stop

```bash
docker compose down          # stops containers, keeps DB data
docker compose down -v       # stops containers AND wipes DB volumes
```

---

## Path B: Local Dev (hot-reload)

Use this when actively developing the server. The database still runs in Docker.

### 1. Start the database

```bash
docker compose up -d db
```

Wait for it to be healthy:

```bash
docker compose ps
# db should show "(healthy)"
```

### 2. Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — the default `POSTGRES_URL` already points to the Docker database:

```
POSTGRES_URL=postgresql+asyncpg://arcshield:arcshield@localhost:5432/arcshield
API_KEY=your-secret-key-here
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Build the dashboard (one-time, or after dashboard changes)

```bash
cd dashboard
npm install
npm run build
cd ..
```

The build output lands in `dashboard/dist/` and is served by FastAPI at `/dashboard`.

### 6. Start the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--reload` watches for Python file changes and restarts automatically.

### 7. (Optional) Dashboard dev server with hot-reload

In a second terminal:

```bash
cd dashboard
npm run dev
```

The Vite dev server runs at `http://localhost:5173/dashboard` and proxies API calls to `http://localhost:8000`.

---

## Smoke Test

Run these after startup to confirm all systems are working:

```bash
API_KEY="your-secret-key-here"
BASE="http://localhost:8000"

# 1. Health
curl "$BASE/health"
# → {"status":"ok"}

# 2. Ingest a test event
curl -s -X POST "$BASE/events" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "pre_env": {"operator_id": "kahn", "shift_phase": "MID"},
    "cause": {
      "trigger_type": "MANUAL",
      "description": "smoke test event"
    },
    "intuition": {"srk_level": "SKILL"},
    "action": {"description": "test action"},
    "result": {
      "outcome_tag": "PREVENTED",
      "graph_weight": 0.5,
      "withhold_sample": false
    }
  }'
# → {"event_id":"550e8400-...","status":"stored"}

# 3. List events
curl -s -H "X-API-Key: $API_KEY" "$BASE/events" | python3 -m json.tool

# 4. Threshold
curl -s -H "X-API-Key: $API_KEY" "$BASE/config/threshold?operator_id=kahn" | python3 -m json.tool

# 5. RAG query
curl -s -H "X-API-Key: $API_KEY" "$BASE/twin/query?cause=smoke+test&limit=3" | python3 -m json.tool
```

---

## Android App Configuration

In `ArcShieldDAQ`, open **PreEnvPrefsStore** and set:

| Setting | Value |
|---|---|
| `server_base_url` | `http://<laptop-ip>:8000` |
| `api_key` | The same `API_KEY` value from `.env` |

Find the laptop's LAN IP:

```bash
# macOS / Linux
ip route get 1 | awk '{print $7; exit}'

# Windows
ipconfig | findstr "IPv4"
```

Make sure the laptop and Android device are on the same Wi-Fi network. If using the plant LAN with a wired laptop, connect the Android device to the same network segment.

---

## API Documentation

Interactive OpenAPI docs are available (no auth required) at:

```
http://localhost:8000/docs
```

---

## Logs

```bash
# Docker Compose
docker compose logs -f api
docker compose logs -f db

# Local dev — logs print directly to the terminal running uvicorn
```

---

## Resetting the Database

```bash
# Docker Compose — wipes all data and starts fresh
docker compose down -v
docker compose up --build

# Local dev — drop and recreate
psql -U arcshield -h localhost arcshield -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
alembic upgrade head
```
