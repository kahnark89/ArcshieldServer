import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag import query_similar
from app.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_rag_text_fallback():
    db = AsyncMock()

    row = MagicMock()
    row.event_id = "550e8400-e29b-41d4-a716-446655440001"
    row.graph_weight = 0.75
    row.similarity = 0.5
    row.event_json = {
        "cause": {"description": "hydraulic pressure spike"},
        "intuition": {"hypothesis": "worn seal"},
        "action": {"description": "shut down press"},
        "result": {"outcome_tag": "PREVENTED"},
    }

    result_mock = MagicMock()
    result_mock.fetchall.return_value = [row]
    db.execute = AsyncMock(return_value=result_mock)

    embed_svc = EmbeddingService()

    results = await query_similar(db, "hydraulic pressure", 5, embed_svc)
    assert len(results) == 1
    assert results[0].cause_description == "hydraulic pressure spike"
    assert results[0].outcome_tag == "PREVENTED"
    assert results[0].similarity_score == 0.5


@pytest.mark.asyncio
async def test_rag_with_embedding():
    db = AsyncMock()

    row = MagicMock()
    row.event_id = "550e8400-e29b-41d4-a716-446655440002"
    row.graph_weight = 0.85
    row.similarity = 0.92
    row.event_json = {
        "cause": {"description": "acoustic anomaly on line 1"},
        "intuition": {"hypothesis": "bearing failure"},
        "action": {"description": "halted production"},
        "result": {"outcome_tag": "RESOLVED"},
    }

    result_mock = MagicMock()
    result_mock.fetchall.return_value = [row]
    db.execute = AsyncMock(return_value=result_mock)

    embed_svc = MagicMock(spec=EmbeddingService)
    embed_svc.is_ready.return_value = True
    embed_svc.embed = AsyncMock(return_value=[0.1] * 384)

    results = await query_similar(db, "strange noise from conveyor", 5, embed_svc)
    assert len(results) == 1
    assert results[0].similarity_score == 0.92
