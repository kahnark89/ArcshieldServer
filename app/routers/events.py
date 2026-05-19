import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database import get_db
from app.models.event import Event
from app.schemas.ciaer_event import CiaerPlusEvent
from app.schemas.api_responses import (
    EventIngestResponse,
    EventSummary,
    EventListResponse,
    FeedbackUpdateResponse,
)
from app.services.embedding import embedding_service

router = APIRouter(prefix="/events", tags=["events"])


def _extract_event_fields(event: CiaerPlusEvent) -> dict:
    tc = event.cause.trigger_context
    scores = tc.signal_scores if tc and tc.signal_scores else None
    return {
        "event_id": uuid.UUID(event.event_id),
        "operator_id": event.pre_env.operator_id,
        "shift_phase": event.pre_env.shift_phase,
        "material_batch_id": event.pre_env.material_batch_id,
        "ambient_temp_f": event.pre_env.ambient_temp_f,
        "trigger_type": event.cause.trigger_type,
        "operational_mode": tc.operational_mode if tc else None,
        "confidence_score": None,
        "gaze_score": scores.gaze if scores else None,
        "hand_score": scores.hand if scores else None,
        "hrv_score": scores.hrv if scores else None,
        "acoustic_score": scores.acoustic if scores else None,
        "srk_level": event.intuition.srk_level,
        "hypothesis_confirmed": event.intuition.hypothesis_confirmed,
        "outcome_tag": event.result.outcome_tag,
        "graph_weight": event.result.graph_weight,
        "withhold_sample": event.result.withhold_sample,
        "operator_validated": (
            tc.feedback.operator_validated if tc and tc.feedback else None
        ),
        "event_json": event.model_dump(mode="json"),
    }


async def _compute_and_store_embedding(event_id: uuid.UUID, cause_description: str, db: AsyncSession):
    if not embedding_service.is_ready():
        return
    try:
        vector = await embedding_service.embed(cause_description)
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        await db.execute(
            text("UPDATE events SET cause_embedding = :vec::vector WHERE event_id = :eid"),
            {"vec": vector_str, "eid": str(event_id)},
        )
        await db.commit()
    except Exception:
        pass


@router.post("", status_code=201, response_model=EventIngestResponse)
async def ingest_event(
    event: CiaerPlusEvent,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    fields = _extract_event_fields(event)
    db_event = Event(**fields, created_at=datetime.now(timezone.utc))
    db.add(db_event)
    await db.commit()

    background_tasks.add_task(
        _compute_and_store_embedding,
        db_event.event_id,
        event.cause.description,
        AsyncSession(db.get_bind()),
    )

    return EventIngestResponse(event_id=str(db_event.event_id), status="stored")


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    operator_id: Optional[str] = None,
    outcome_tag: Optional[str] = None,
    operator_validated: Optional[bool] = None,
    srk_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Event)
    if operator_id:
        stmt = stmt.where(Event.operator_id == operator_id)
    if outcome_tag:
        stmt = stmt.where(Event.outcome_tag == outcome_tag)
    if operator_validated is not None:
        stmt = stmt.where(Event.operator_validated == operator_validated)
    if srk_level:
        stmt = stmt.where(Event.srk_level == srk_level)
    if date_from:
        stmt = stmt.where(Event.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(Event.created_at <= datetime.fromisoformat(date_to))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Event.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    return EventListResponse(
        total=total,
        page=page,
        limit=limit,
        results=[
            EventSummary(
                event_id=str(r.event_id),
                operator_id=r.operator_id,
                trigger_type=r.trigger_type,
                outcome_tag=r.outcome_tag,
                graph_weight=r.graph_weight,
                operator_validated=r.operator_validated,
                shift_phase=r.shift_phase,
                srk_level=r.srk_level,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
    )


@router.get("/{event_id}")
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Event, uuid.UUID(event_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return row.event_json


@router.patch("/{event_id}/feedback", response_model=FeedbackUpdateResponse)
async def update_feedback(
    event_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Event, uuid.UUID(event_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")

    operator_validated = body.get("operator_validated")
    notes = body.get("notes")

    if operator_validated is not None:
        row.operator_validated = bool(operator_validated)

    event_json = dict(row.event_json)
    cause = event_json.get("cause", {})
    tc = cause.get("trigger_context", {}) or {}
    feedback = tc.get("feedback", {}) or {}
    if operator_validated is not None:
        feedback["operator_validated"] = operator_validated
    if notes is not None:
        feedback["notes"] = notes
    tc["feedback"] = feedback
    cause["trigger_context"] = tc
    event_json["cause"] = cause
    row.event_json = event_json

    await db.commit()
    return FeedbackUpdateResponse(event_id=event_id, status="updated")
