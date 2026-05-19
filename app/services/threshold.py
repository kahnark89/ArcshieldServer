from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.models.threshold import ThresholdHistory, CurrentThreshold

THRESHOLD_MIN = 0.55
THRESHOLD_MAX = 0.80


async def recalculate_threshold(db: AsyncSession, operator_id: str) -> None:
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    fp_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM events "
            "WHERE operator_id = :oid AND operator_validated = FALSE "
            "AND created_at >= :since"
        ),
        {"oid": operator_id, "since": one_hour_ago},
    )
    fp_count = fp_result.scalar() or 0

    tp_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM events "
            "WHERE operator_id = :oid AND operator_validated = TRUE "
            "AND created_at >= :since"
        ),
        {"oid": operator_id, "since": one_hour_ago},
    )
    tp_count = tp_result.scalar() or 0

    current = await db.get(CurrentThreshold, operator_id)
    if current is None:
        current = CurrentThreshold(operator_id=operator_id)
        db.add(current)

    old_value = current.threshold_adjusted
    new_value = old_value

    fp_rate = float(fp_count)
    direction = None

    if fp_rate > 2:
        new_value = min(old_value + 0.03, THRESHOLD_MAX)
        direction = "UP"
    elif fp_rate < 0.5 and tp_count > 1:
        new_value = max(old_value - 0.03, THRESHOLD_MIN)
        direction = "DOWN"

    if direction is not None:
        current.threshold_adjusted = round(new_value, 4)
        current.updated_at = datetime.now(timezone.utc)

        history = ThresholdHistory(
            operator_id=operator_id,
            threshold_value=current.threshold_adjusted,
            direction=direction,
            fp_rate_hourly=fp_rate,
            tp_count_hourly=int(tp_count),
        )
        db.add(history)
        await db.commit()
