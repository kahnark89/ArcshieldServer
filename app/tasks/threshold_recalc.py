from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.threshold import recalculate_threshold

scheduler = AsyncIOScheduler()


async def _run_threshold_recalc():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT DISTINCT operator_id FROM events "
                "WHERE created_at >= now() - interval '24 hours'"
            )
        )
        operator_ids = [row[0] for row in result.fetchall()]

    for operator_id in operator_ids:
        async with AsyncSessionLocal() as db:
            await recalculate_threshold(db, operator_id)


def start_scheduler():
    scheduler.add_job(_run_threshold_recalc, "interval", hours=1, id="threshold_recalc")
    scheduler.start()


def stop_scheduler():
    scheduler.shutdown(wait=False)
