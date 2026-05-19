from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.threshold import CurrentThreshold, ThresholdHistory
from app.schemas.api_responses import ThresholdResponse, ThresholdHistoryResponse, ThresholdHistoryEntry
from sqlalchemy import select

router = APIRouter(prefix="/config", tags=["config"])

THRESHOLD_MIN = 0.55
THRESHOLD_MAX = 0.80

_DEFAULTS = {
    "SETUP": {"immediate": 0.70, "counter": 0.55, "adjusted": 0.70},
    "STEADY": {"immediate": 0.75, "counter": 0.60, "adjusted": 0.65},
    "TROUBLESHOOTING": {"immediate": 0.65, "counter": 0.55, "adjusted": 0.60},
}


@router.get("/threshold", response_model=ThresholdResponse)
async def get_threshold(
    operator_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(CurrentThreshold, operator_id)
    if row is None:
        d = _DEFAULTS["STEADY"]
        return ThresholdResponse(
            threshold_immediate=d["immediate"],
            threshold_counter=d["counter"],
            threshold_adjusted=d["adjusted"],
            mode="STEADY",
        )
    return ThresholdResponse(
        threshold_immediate=row.threshold_immediate,
        threshold_counter=row.threshold_counter,
        threshold_adjusted=row.threshold_adjusted,
        mode=row.mode,
    )


@router.patch("/threshold")
async def manual_threshold_override(
    body: dict,
    operator_id: str = Query("default"),
    db: AsyncSession = Depends(get_db),
):
    value = body.get("threshold_adjusted")
    if value is None:
        raise HTTPException(status_code=422, detail="threshold_adjusted required")
    if not (THRESHOLD_MIN <= float(value) <= THRESHOLD_MAX):
        raise HTTPException(
            status_code=422,
            detail=f"threshold_adjusted must be in [{THRESHOLD_MIN}, {THRESHOLD_MAX}]",
        )

    row = await db.get(CurrentThreshold, operator_id)
    if row is None:
        row = CurrentThreshold(operator_id=operator_id)
        db.add(row)

    row.threshold_adjusted = round(float(value), 4)
    row.updated_at = datetime.now(timezone.utc)

    history = ThresholdHistory(
        operator_id=operator_id,
        threshold_value=row.threshold_adjusted,
        direction="MANUAL",
        fp_rate_hourly=None,
        tp_count_hourly=None,
    )
    db.add(history)
    await db.commit()
    return {"operator_id": operator_id, "threshold_adjusted": row.threshold_adjusted, "status": "updated"}


@router.get("/threshold/history", response_model=ThresholdHistoryResponse)
async def get_threshold_history(
    operator_id: str = Query("default"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ThresholdHistory)
        .where(ThresholdHistory.operator_id == operator_id)
        .order_by(ThresholdHistory.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return ThresholdHistoryResponse(
        operator_id=operator_id,
        entries=[
            ThresholdHistoryEntry(
                threshold_value=r.threshold_value,
                direction=r.direction,
                fp_rate_hourly=r.fp_rate_hourly,
                tp_count_hourly=r.tp_count_hourly,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
    )
