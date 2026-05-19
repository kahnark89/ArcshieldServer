import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app

SAMPLE_EVENT = {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "pre_env": {
        "operator_id": "kahn",
        "shift_phase": "STEADY",
        "material_batch_id": None,
        "ambient_temp_f": 72.5,
        "sensory_baseline": None,
    },
    "cause": {
        "description": "Hydraulic pressure spike detected on press 3",
        "trigger_type": "AUTOMATIC",
        "trigger_channels": ["hrv", "acoustic"],
        "trigger_context": {
            "signal_scores": {"gaze": 0.62, "hand": 0.71, "hrv": 0.80, "acoustic": 0.75},
            "temporal_modifier": 1.1,
            "operational_mode": "STEADY",
            "sensor_context": {},
            "feedback": {"operator_validated": None, "notes": None},
        },
        "timestamp": "2026-05-19T10:30:00Z",
    },
    "intuition": {
        "srk_level": "RULE",
        "hypothesis": "Worn seal on hydraulic cylinder",
        "hypothesis_confirmed": True,
        "confidence": 0.78,
    },
    "action": {"description": "Shut down press and called maintenance", "tool_used": "radio"},
    "shadow_actions": [
        {"description": "Continue running", "rejection_rationale": "Too risky", "srk_level": "SKILL"}
    ],
    "effect": {"observed_outcome": "Pressure normalized after shutdown", "timestamp": "2026-05-19T10:35:00Z"},
    "result": {
        "outcome_tag": "PREVENTED",
        "notes": "Seal replaced, press back in service",
        "graph_weight": 0.85,
        "withhold_sample": False,
    },
    "biometric_snapshot": {
        "hr_bpm": 88,
        "hrv_rmssd_ms": 32.5,
        "skin_temp_c": 34.1,
        "source_device": "polar_h10",
    },
}

HEADERS = {"X-API-Key": "changeme"}


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.get_bind = MagicMock(return_value=MagicMock())
    return session


@pytest.mark.asyncio
async def test_ingest_event_success(mock_db_session):
    from app.database import get_db

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/events", json=SAMPLE_EVENT, headers=HEADERS)
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "stored"
    assert "event_id" in data


@pytest.mark.asyncio
async def test_ingest_event_missing_required_field():
    bad_event = dict(SAMPLE_EVENT)
    del bad_event["cause"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/events", json=bad_event, headers=HEADERS)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_missing_api_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/events", json=SAMPLE_EVENT)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_no_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
