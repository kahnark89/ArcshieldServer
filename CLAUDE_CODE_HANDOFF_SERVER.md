# Claude Code Handoff — arcshield-corpus Server

**Project:** arcshield-corpus (event corpus + web dashboard for ArcShield)
**Author/Operator:** Kahn Capps, Capps Family Enterprises, Helena-West Helena, AR
**Deployment target:** PPVC Line 1, Hollowell Industries (local plant network)
**Handoff date:** 2026-05-19
**Source:** Produced in the ArcShieldDAQ Android session to hand the server build off to a new Claude Code repo.

---

## What this server is (one paragraph)

`arcshield-corpus` is the server half of a two-unit system. The other unit is the native Android app (`ArcShieldDAQ`). The server does everything the Android app deliberately does not: it stores the growing CIAER+ event corpus, serves a RAG (retrieval-augmented generation) endpoint that the AI Twin uses to ground its guidance in past events, and hosts a web dashboard where Kahn reviews captures, labels true/false positives, and tunes detection thresholds. The Android app is capture-only; all review, analytics, and model-serving logic lives here.

---

## System architecture overview

```
+--------------------+     HTTP (plant LAN)    +----------------------+
|  Android App       |  ──────────────────────▶ |  arcshield-corpus    |
|  (ArcShieldDAQ)    |                          |  (this repo)         |
|                    |  POST /events            |                      |
|  LocalServerSink   | ─────────────────────── |  FastAPI             |
|  TwinClient        |  GET  /twin/query        |  PostgreSQL          |
|  SyncWorker        |  GET  /config/threshold  |  TimescaleDB ext.    |
+--------------------+                          |                      |
                                                |  Web Dashboard       |
                                                |  (React or Vue)      |
+--------------------+                          |                      |
|  Kahn (browser)    |  ◀────────────────────── |  /dashboard          |
|  desktop/tablet    |  WebSocket + REST        |                      |
+--------------------+                          +----------------------+
```

**Key constraint:** Gen 1 deployment is local to the plant network. No cloud. No multi-tenancy. Single operator (Kahn). Single facility (Hollowell Industries PPVC Line 1). Cloud migration is a configuration change when a second facility appears — design for it, but don't build it now.

---

## Two primary roles

### Role 1 — Event corpus and RAG

- Accept CIAER+ events POSTed by the Android app's `LocalServerSink`.
- Persist them to PostgreSQL (structured CIAER fields) + TimescaleDB (raw sensor time-series for replay).
- Serve a RAG query endpoint: given a cause description, return the N most relevant past events. The Android `TwinClient` calls this endpoint when it wants grounding for its Twin guidance.
- Track `graph_weight` and `withhold_sample` per event to drive the Twin's sampling policy (withhold a calibrated subset of events to produce counterfactual training samples — see whitepaper §10.12).
- Serve current threshold config back to the Android app on demand.

### Role 2 — Web dashboard

- **Event review:** Browse captured CIAER+ events. Filter by operator, shift, outcome tag, signal scores.
- **FP/TP labeling:** After each automatic trigger, the operator's post-hoc binary label (`operator_validated: true/false`) should be storable here. The Android app collects it during the Result phase; the server stores it and surfaces it in the dashboard.
- **Sensor replay:** Synchronized playback of pre-trigger video clip (from `VisualSnapshot.framePath`), audio clip, and biometric overlay (HR/RMSSD trace). This is why TimescaleDB matters — efficient range queries on raw sensor time-series.
- **Threshold tuning:** Display the dynamic threshold adjustment log (detection-spec §7.5). Allow manual override within [0.55, 0.80]. Push new threshold back to app via the `/config/threshold` endpoint.
- **Knowledge graph visualization:** Eventually — relationships between cause patterns, outcomes, and operator responses. Phase 2 dashboard feature, not day-one.

---

## CIAER+ schema — the contract

The schema lives at `schema/ciaer_plus_v1.json` in the `ArcShieldDAQ` Android repo. **The server must accept events in exactly this shape.** Do not invent server-side field names — copy or reference that schema file.

### Top-level event structure

```json
{
  "event_id": "uuid",
  "capture_device": { ... },
  "pre_env": {
    "operator_id": "string",
    "shift_phase": "STARTUP | MID_SHIFT | END_SHIFT | BATCH_CHANGE",
    "material_batch_id": "string | null",
    "ambient_temp_f": "float | null",
    "recent_events_summary": "string | null",
    "sensory_baseline": {
      "acoustic": { "spectral_centroid_hz": float, "dominant_freq_hz": float, "amplitude_dbfs": float, "freq_histogram": [32 floats] },
      "vibration": { "dominant_freq_hz": float, "rms_acceleration": float, "peak_acceleration": float, "freq_histogram": [32 floats] },
      "visual": { "motion_score": float, "luminance": float, "frame_path": "string | null", "capture_mode": "string" },
      "olfactory": { "annotation": "string | null", "intensity": "int | null", "voc_ppb": "float | null", "wake_word_triggered": bool },
      "thermal": { "ambient_temp_f": "float | null", "source_label": "string" }
    }
  },
  "cause": {
    "description": "string",
    "trigger_type": "AUTOMATIC | MANUAL",
    "trigger_channels": ["hrv", "acoustic", "hand_pose", "fusion_threshold", ...],
    "trigger_context": {
      "signal_scores": { "gaze": float, "hand": float, "hrv": float, "acoustic": float },
      "temporal_modifier": float,
      "operational_mode": "SETUP | STEADY | TROUBLESHOOTING",
      "sensor_context": { ... },
      "feedback": { "operator_validated": bool | null, "notes": "string | null" }
    },
    "timestamp": "ISO 8601"
  },
  "intuition": {
    "srk_level": "SKILL | RULE | KNOWLEDGE",
    "hypothesis": "string",
    "hypothesis_confirmed": bool | null,
    "confidence": float | null
  },
  "action": { "description": "string", "tool_used": "string | null" },
  "shadow_actions": [
    { "description": "string", "rejection_rationale": "string", "srk_level": "string" }
  ],
  "effect": { "observed_outcome": "string", "timestamp": "ISO 8601 | null" },
  "result": {
    "outcome_tag": "PREVENTED | RESOLVED | IMPROVED | NO_CHANGE | WORSE | UNKNOWN",
    "notes": "string | null",
    "graph_weight": float,
    "withhold_sample": bool
  },
  "biometric_snapshot": {
    "hr_bpm": int | null,
    "hrv_rmssd_ms": float | null,
    "skin_temp_c": float | null,
    "source_device": "polar_h10 | polar_verity_sense"
  }
}
```

**Important fields for the server:**
- `result.graph_weight` (0.10–1.00): drives Twin sampling policy. Computed by the Android app's `SensoryEventRepository`:
  - Base 0.5
  - +0.20 if `intuition.hypothesis_confirmed == true`
  - +0.15 if `result.outcome_tag in [PREVENTED, RESOLVED]`
  - −0.10 if `intuition.srk_level == SKILL`
  - Clamped to [0.10, 1.00]
- `result.withhold_sample`: the server dashboard can set this to `true` for events the Twin should exclude from its guidance. Default `false`.
- `cause.trigger_context.feedback.operator_validated`: set during Result phase. `true` = genuine insight moment (TP), `false` = false positive, `null` = not yet labeled.

---

## API endpoints (required at launch)

### POST /events
Accept a single CIAER+ event JSON body. Validate against the schema. Persist.

```
POST /events
Content-Type: application/json
Body: { ...CiaerPlusEvent... }

Response 201: { "event_id": "uuid", "status": "stored" }
Response 422: { "error": "validation error details" }
```

Android `LocalServerSink` POSTs here. The Android app queues events in Room and the `SyncWorker` drains the queue via this endpoint when connectivity allows.

### GET /twin/query
RAG endpoint. Android `TwinClient` calls this when the operator reaches the Intuition phase and wants grounding.

```
GET /twin/query?cause=<url-encoded cause description>&limit=5

Response 200: {
  "results": [
    {
      "event_id": "uuid",
      "cause_description": "string",
      "intuition_hypothesis": "string",
      "action_description": "string",
      "outcome_tag": "PREVENTED | ...",
      "graph_weight": float,
      "similarity_score": float
    }
  ]
}
```

Initial RAG implementation: embed cause descriptions with a lightweight embedding model (sentence-transformers `all-MiniLM-L6-v2` is sufficient at first). Store embeddings in pgvector. At query time, embed the incoming cause description and retrieve top-N by cosine similarity. Filter out `withhold_sample = true` events.

### GET /config/threshold
Return the current fusion threshold for the operator. Android app checks this on shift start.

```
GET /config/threshold?operator_id=<id>

Response 200: {
  "threshold_immediate": 0.75,
  "threshold_counter": 0.60,
  "threshold_adjusted": 0.65,
  "mode": "STEADY"
}
```

### PATCH /events/{event_id}/feedback
Update an event's FP/TP label after the dashboard review.

```
PATCH /events/{event_id}/feedback
Body: { "operator_validated": true, "notes": "optional string" }

Response 200: { "event_id": "uuid", "status": "updated" }
```

### GET /dashboard (and sub-routes)
Serves the web dashboard SPA. All dashboard routes return the SPA entry point; client-side routing handles the rest.

---

## Dynamic threshold adjustment (detection-spec §7.5)

The spec defines:
```
IF operator's hourly FP count > 2:
    INCREASE threshold by 0.03
IF operator's hourly FP count < 0.5 AND TP count > 1:
    DECREASE threshold by 0.03
LIMIT threshold to range [0.55, 0.80]
```

**Server responsibilities:**
- Track TP/FP counts per operator per hour using the `operator_validated` field on incoming events.
- Run a scheduled task (e.g., APScheduler or a cron-style background task) to recompute the adjusted threshold every hour.
- Persist the current threshold in the DB so `GET /config/threshold` always returns the current value.
- Log each threshold adjustment with timestamp, direction, and old/new values.

**Android responsibilities (already implemented):**
- `OperationalModeDetector.currentMode()` reads recent event outcomes locally and returns SETUP/STEADY/TROUBLESHOOTING.
- The Android `FusionEngine` applies mode-based thresholds: SETUP 0.70, STEADY 0.65, TROUBLESHOOTING 0.60.
- The server's dynamic adjustment is a second-order refinement on top of these base values — the server pushes a `threshold_adjusted` value that the Android applies on the next shift start.

---

## Tech stack

| Layer | Choice | Notes |
|---|---|---|
| API framework | FastAPI (Python 3.11+) | Async, OpenAPI auto-docs, well-typed |
| DB | PostgreSQL 16 | Primary storage for CIAER events |
| Time-series | TimescaleDB extension on PostgreSQL | Raw sensor streams, efficient range queries for replay |
| Vector search | pgvector extension on PostgreSQL | Embedding storage for RAG |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | Lightweight; no GPU needed initially |
| Background tasks | APScheduler (or Celery if queue grows) | Threshold recalculation, sync tasks |
| Web dashboard | React + Vite | Or Vue — Kahn's preference, ask before starting |
| Dashboard charts | Chart.js or Recharts | Signal replay timeline, threshold history |
| ORM | SQLAlchemy 2.0 (async) + Alembic for migrations | |
| Validation | Pydantic v2 | Schema validation on ingest |
| Dev server | uvicorn | |

---

## Database schema (PostgreSQL)

### Table: `events`

```sql
CREATE TABLE events (
    event_id        UUID PRIMARY KEY,
    operator_id     TEXT NOT NULL,
    shift_phase     TEXT,
    material_batch_id TEXT,
    ambient_temp_f  REAL,
    trigger_type    TEXT NOT NULL,          -- AUTOMATIC | MANUAL
    operational_mode TEXT,                  -- SETUP | STEADY | TROUBLESHOOTING
    confidence_score REAL,                  -- adjusted fusion score at fire
    gaze_score      REAL,
    hand_score      REAL,
    hrv_score       REAL,
    acoustic_score  REAL,
    srk_level       TEXT,                   -- SKILL | RULE | KNOWLEDGE
    hypothesis_confirmed BOOLEAN,
    outcome_tag     TEXT,
    graph_weight    REAL,
    withhold_sample BOOLEAN DEFAULT FALSE,
    operator_validated BOOLEAN,             -- FP/TP label; null until labeled
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_json      JSONB NOT NULL,         -- full CiaerPlusEvent for replay/RAG
    cause_embedding VECTOR(384)             -- pgvector; all-MiniLM-L6-v2 output
);

CREATE INDEX events_operator_created ON events (operator_id, created_at DESC);
CREATE INDEX events_outcome ON events (outcome_tag);
CREATE INDEX events_validated ON events (operator_validated) WHERE operator_validated IS NOT NULL;
```

### Table: `sensor_streams` (TimescaleDB hypertable)

For raw biometric + acoustic replay. The Android app includes a pre-trigger window in the CIAER event's `sensor_context` fields; the server can optionally store fine-grained time-series here if the Android app sends it.

```sql
CREATE TABLE sensor_streams (
    event_id    UUID NOT NULL REFERENCES events(event_id),
    ts          TIMESTAMPTZ NOT NULL,
    signal_name TEXT NOT NULL,    -- 'hr_bpm', 'hrv_rmssd_ms', 'audio_amplitude_db', etc.
    value       REAL NOT NULL
);
SELECT create_hypertable('sensor_streams', 'ts');
CREATE INDEX sensor_event_signal ON sensor_streams (event_id, signal_name, ts DESC);
```

### Table: `threshold_history`

```sql
CREATE TABLE threshold_history (
    id              SERIAL PRIMARY KEY,
    operator_id     TEXT NOT NULL,
    threshold_value REAL NOT NULL,
    direction       TEXT,         -- 'UP' | 'DOWN' | 'MANUAL'
    fp_rate_hourly  REAL,
    tp_count_hourly INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Android integration: what's already built

These are the Android-side integration points that are already implemented in `ArcShieldDAQ`. The server must satisfy their expectations.

### `LocalServerSink`

Location: `app/src/main/java/com/arcshield/app/sync/LocalServerSink.kt`

Currently a stub. When you bootstrap the server, update the base URL (configurable in `PreEnvPrefsStore` via a `server_base_url` key, or hardcoded initially). The sink:
- Takes a serialized `CiaerPlusEvent` JSON string.
- POSTs to `{base_url}/events` with `Content-Type: application/json`.
- On 201, marks the event as synced in Room.
- On failure, leaves it in the queue for retry.

`SyncWorker` at `com.arcshield.app.sync.SyncWorker` runs as a `CoroutineWorker` and drains the Room queue through `LocalServerSink`.

### `TwinClient`

Location: `app/src/main/java/com/arcshield/app/twin/TwinClient.kt`

Currently a stub. When the server's RAG endpoint is ready, implement this as an OkHttp call to `{base_url}/twin/query?cause={url_encoded_cause}&limit=5`. The Android app calls `TwinClient.query(causeDescription)` during the Intuition phase and renders the results as context cards.

### Config endpoint

The Android app should call `GET {base_url}/config/threshold` on shift start and apply `threshold_adjusted` in `FusionEngine`. This wiring is not yet implemented in the Android app — it's a TODO once the server endpoint exists.

---

## RAG implementation guide

For the initial deployment (fewer than 200 events), the RAG is purely retrieval — no LoRA fine-tuning yet.

**Embedding pipeline:**

1. On event ingest (`POST /events`), extract `cause.description`.
2. Embed with `sentence-transformers all-MiniLM-L6-v2` → 384-dim float vector.
3. Store in `events.cause_embedding` (pgvector `VECTOR(384)` column).

**Query pipeline:**

1. Receive `GET /twin/query?cause=...`.
2. Embed the incoming cause description.
3. Query: `SELECT event_id, cause_description, ... FROM events WHERE withhold_sample = FALSE ORDER BY cause_embedding <=> $1 LIMIT $2`.
4. Return top-N results with similarity scores.

**LoRA fine-tuning (future, not day-one):**
- Activates when the corpus reaches ~200 validated events.
- Training runs server-side (or on a separate GPU machine). Server re-exposes the fine-tuned model's endpoint for `TwinClient` queries.
- Do not implement LoRA now — the endpoint shape doesn't change when it arrives.

---

## Web dashboard requirements

Build the dashboard as a separate SPA (React or Vue + Vite) served from `/dashboard` by FastAPI's `StaticFiles`. The FastAPI backend serves JSON APIs; the SPA calls them.

### Required views at launch

**1. Event list (`/dashboard/events`)**
- Paginated table: timestamp, operator_id, trigger_type, outcome_tag, graph_weight, operator_validated (TP/FP badge), shift_phase.
- Filters: date range, outcome_tag, operator_validated (labeled / unlabeled), srk_level.
- Click row → event detail view.

**2. Event detail (`/dashboard/events/{id}`)**
- Full CIAER+ event rendered in human-readable card layout.
- Signal scores bar chart (gaze, hand, HRV, acoustic).
- Sensory baseline snapshot table.
- Shadow actions list.
- FP/TP labeling UI: two buttons ("Genuine insight" / "False positive") that call `PATCH /events/{id}/feedback`.
- Video frame thumbnail if `visual.frame_path` is set (serve the file from `GET /media/frames/{filename}`).

**3. Threshold dashboard (`/dashboard/thresholds`)**
- Current threshold values (immediate, counter, adjusted).
- Threshold history chart (line chart, adjustments over time).
- Manual override input (within [0.55, 0.80]).
- Hourly TP/FP rate chart.

**4. Sensor replay (`/dashboard/events/{id}/replay`) — Phase 2**
- Synchronized playback of pre-trigger sensor stream.
- Timeline with HR trace, acoustic amplitude trace, score trace.
- Not needed for initial deployment but plan the data model for it now (TimescaleDB `sensor_streams` table above).

---

## Deployment (local plant network)

- Run on a small local machine or NUC at Hollowell, same network as Kahn's phone.
- Phone connects via Wi-Fi or wired LAN. No internet required for the server's core function.
- Open-Meteo calls originate from the Android app, not the server.
- Postgres + TimescaleDB installed locally. No managed DB needed.
- Use Docker Compose for local dev + production: one container for FastAPI/uvicorn, one for Postgres + extensions, one for the SPA build (or serve static from FastAPI).
- `arcshield-corpus` should include a `docker-compose.yml` and a `.env.example` with:
  - `POSTGRES_URL`
  - `SERVER_HOST` / `SERVER_PORT`
  - `EMBEDDING_MODEL` (default: `all-MiniLM-L6-v2`)
  - `MEDIA_ROOT` (path where Android-uploaded frame JPEGs are stored)

**Base URL for the Android app:** Configurable. Default to `http://arcshield-server.local:8000` (mDNS) or `http://192.168.x.x:8000`. Stored in Android `PreEnvPrefsStore` under `server_base_url`.

---

## Project layout (recommended)

```
arcshield-corpus/
├── CLAUDE.md                        ← project memory (create from this handoff)
├── CLAUDE_CODE_HANDOFF_SERVER.md    ← this file
├── docker-compose.yml
├── .env.example
├── alembic/                         ← DB migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py                      ← FastAPI app, router mounts
│   ├── config.py                    ← settings (pydantic-settings)
│   ├── database.py                  ← async SQLAlchemy engine + session
│   ├── models/
│   │   ├── event.py                 ← SQLAlchemy ORM model for `events`
│   │   └── sensor_stream.py
│   ├── schemas/
│   │   ├── ciaer_event.py           ← Pydantic v2 model matching ciaer_plus_v1.json
│   │   └── api_responses.py
│   ├── routers/
│   │   ├── events.py                ← POST /events, GET /events, PATCH /events/{id}/feedback
│   │   ├── twin.py                  ← GET /twin/query
│   │   ├── config.py                ← GET /config/threshold, PATCH /config/threshold
│   │   └── media.py                 ← GET /media/frames/{filename}
│   ├── services/
│   │   ├── embedding.py             ← sentence-transformers wrapper
│   │   ├── rag.py                   ← query pipeline
│   │   └── threshold.py             ← dynamic threshold logic
│   └── tasks/
│       └── threshold_recalc.py      ← APScheduler job
└── dashboard/                       ← SPA (React or Vue)
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── views/
        │   ├── EventList.tsx
        │   ├── EventDetail.tsx
        │   ├── ThresholdDashboard.tsx
        │   └── SensorReplay.tsx
        └── api/
            └── client.ts            ← typed fetch wrappers for FastAPI endpoints
```

---

## Pydantic schema (match the Android JSON exactly)

The Pydantic models in `app/schemas/ciaer_event.py` must accept the JSON shape the Android app serializes. Key notes:

- The Android app uses `kotlinx.serialization` with `@SerialName` snake_case field names. All JSON keys are `snake_case`.
- All optional fields should be `Optional[...] = None` in Pydantic — the Android app may omit fields that weren't captured (e.g., `sensory_baseline` before the first shift-start).
- `cause.trigger_context` is a nested object present only when `trigger_type == "AUTOMATIC"`.
- `result.graph_weight` is always present (default 0.5 in the Android app).
- `shadow_actions` is a list, possibly empty.
- `biometric_snapshot` may be null if Polar hasn't connected yet.

---

## What NOT to build (scope constraints)

- **Multi-tenancy:** Single operator (Kahn), single facility (PPVC Line 1). No tenant isolation, no enterprise auth. A simple static API key for the Android app → server connection is sufficient for Gen 1.
- **Cloud deployment:** Local network only for Gen 1. Design with `POSTGRES_URL` env var so cloud migration is a config swap.
- **LMS integration:** Paulson, Routsis, Cornerstone — out of scope.
- **LoRA training infrastructure:** Placeholder the endpoint shape; don't build the training pipeline yet.
- **Cross-operator aggregation:** One operator. No aggregation dashboards.
- **SOC2 / security hardening:** Personal use deployment. A self-signed TLS cert or plain HTTP on the LAN is acceptable.
- **In-app Android dashboard:** The Android app is capture-only. Do not replicate dashboard functionality there.

---

## Development conventions

- **Python 3.11+.** Use `asyncio` throughout. No sync blocking in request handlers.
- **Pydantic v2** for all validation. Use `model_validate` not `parse_obj`.
- **SQLAlchemy 2.0 async** with `AsyncSession`. No sync ORM calls.
- **Alembic** for every schema change. Never `ALTER TABLE` manually in prod.
- **FastAPI dependency injection** for DB sessions, settings, services. Keep routers thin.
- **OpenAPI docs** auto-generated by FastAPI — use them as the API contract. Accessible at `/docs`.
- **Tests:** pytest + httpx `AsyncClient` for route tests. At minimum, test the event ingest and RAG query paths.

---

## First steps for a new Claude Code session in this repo

1. Read this file and `CLAUDE.md` (once created).
2. Scaffold the project: `pyproject.toml` (or `requirements.txt`), `docker-compose.yml`, FastAPI `main.py`, and Alembic init.
3. Implement the `events` table migration and the Pydantic `CiaerEvent` schema that matches `ciaer_plus_v1.json`.
4. Implement `POST /events` with validation + persistence. No embedding yet — store `null` in `cause_embedding` column initially.
5. Implement `GET /twin/query` with a simple text-search fallback (PostgreSQL `ILIKE` on `event_json->>'description'`) before the embedding pipeline is ready.
6. Set up the embedding pipeline and backfill existing events.
7. Implement `GET /config/threshold` and the threshold history table.
8. Build the dashboard SPA (event list + event detail + FP/TP labeling first; threshold chart second).
9. Wire `LocalServerSink` in the Android app once the `/events` endpoint is stable.

---

## Reference: Android app expectations

The server must be running before these Android features become useful:

| Android component | Server endpoint | When called |
|---|---|---|
| `SyncWorker` | `POST /events` | Background, on connectivity. Drains Room queue. |
| `TwinClient` | `GET /twin/query` | During Intuition phase of CIAER capture. |
| (future) FusionEngine | `GET /config/threshold` | On shift start. |
| (future) Result phase | `PATCH /events/{id}/feedback` | After operator labels TP/FP. |

**Media files:** The Android app saves camera frames to `getExternalFilesDir("frames")` on the phone. The server should eventually accept these via `POST /media/frames` (multipart upload) so the dashboard can replay them. This is a Phase 2 feature — Phase 1 just stores the frame path string in the event JSON.

---

## Open questions for Kahn

1. **Dashboard framework preference:** React or Vue for the SPA? Both work; just need a decision before starting the frontend.
2. **Server hardware:** Which machine at Hollowell runs this? NUC, mini-PC, old workstation? Affects whether Docker Compose or a direct install is cleaner.
3. **Static API key or per-operator auth?** For Gen 1 (single operator, LAN), a shared static key in `.env` is fine. Confirm this is acceptable or if you want a simple login.
4. **Frame upload:** Should the Android app upload the pre-trigger video frame to the server immediately after capture, or just store the path? Path-only is simpler for Gen 1 but prevents dashboard replay if the phone isn't accessible.
5. **LoRA trigger:** You said ~200 events. Is that 200 total, or 200 labeled (operator_validated not null)? This affects how we design the threshold in the embedding pipeline's training trigger.

---

## Change log

- **2026-05-19** — Initial handoff document created from ArcShieldDAQ session. Covers server architecture, API contracts, database schema, RAG design, dashboard requirements, and Android integration points.
