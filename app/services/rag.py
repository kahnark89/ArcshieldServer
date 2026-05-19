from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.event import Event
from app.schemas.api_responses import TwinQueryResult
from app.services.embedding import EmbeddingService


async def query_similar(
    db: AsyncSession,
    cause: str,
    limit: int,
    embedding_service: EmbeddingService,
) -> list[TwinQueryResult]:
    if embedding_service.is_ready():
        vector = await embedding_service.embed(cause)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        stmt = text(
            """
            SELECT
                event_id,
                event_json,
                graph_weight,
                1 - (cause_embedding <=> :vec::vector) AS similarity
            FROM events
            WHERE withhold_sample = FALSE
              AND cause_embedding IS NOT NULL
            ORDER BY cause_embedding <=> :vec::vector
            LIMIT :lim
            """
        )
        result = await db.execute(stmt, {"vec": vector_str, "lim": limit})
        rows = result.fetchall()
    else:
        pattern = f"%{cause}%"
        stmt = text(
            """
            SELECT
                event_id,
                event_json,
                graph_weight,
                0.5 AS similarity
            FROM events
            WHERE withhold_sample = FALSE
              AND (event_json->>'cause')::text ILIKE :pattern
            ORDER BY created_at DESC
            LIMIT :lim
            """
        )
        result = await db.execute(stmt, {"pattern": pattern, "lim": limit})
        rows = result.fetchall()

    results: list[TwinQueryResult] = []
    for row in rows:
        ej = row.event_json
        cause_desc = ej.get("cause", {}).get("description", "")
        intuition = ej.get("intuition", {})
        action = ej.get("action", {})
        result_section = ej.get("result", {})
        results.append(
            TwinQueryResult(
                event_id=str(row.event_id),
                cause_description=cause_desc,
                intuition_hypothesis=intuition.get("hypothesis", ""),
                action_description=action.get("description", ""),
                outcome_tag=result_section.get("outcome_tag"),
                graph_weight=float(row.graph_weight or 0.5),
                similarity_score=float(row.similarity),
            )
        )
    return results
