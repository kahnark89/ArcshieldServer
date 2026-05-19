import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_recalculate_no_change():
    from app.services.threshold import recalculate_threshold

    db = AsyncMock()
    fp_result = MagicMock()
    fp_result.scalar.return_value = 1
    tp_result = MagicMock()
    tp_result.scalar.return_value = 1

    db.execute = AsyncMock(side_effect=[fp_result, tp_result])

    current = MagicMock()
    current.threshold_adjusted = 0.65
    db.get = AsyncMock(return_value=current)

    await recalculate_threshold(db, "kahn")
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_recalculate_fp_too_high():
    from app.services.threshold import recalculate_threshold

    db = AsyncMock()
    fp_result = MagicMock()
    fp_result.scalar.return_value = 3
    tp_result = MagicMock()
    tp_result.scalar.return_value = 0

    db.execute = AsyncMock(side_effect=[fp_result, tp_result])

    current = MagicMock()
    current.threshold_adjusted = 0.65
    db.get = AsyncMock(return_value=current)
    db.add = MagicMock()

    await recalculate_threshold(db, "kahn")
    assert round(current.threshold_adjusted, 4) == 0.68
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_recalculate_tp_high_fp_low():
    from app.services.threshold import recalculate_threshold

    db = AsyncMock()
    fp_result = MagicMock()
    fp_result.scalar.return_value = 0
    tp_result = MagicMock()
    tp_result.scalar.return_value = 3

    db.execute = AsyncMock(side_effect=[fp_result, tp_result])

    current = MagicMock()
    current.threshold_adjusted = 0.65
    db.get = AsyncMock(return_value=current)
    db.add = MagicMock()

    await recalculate_threshold(db, "kahn")
    assert round(current.threshold_adjusted, 4) == 0.62
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_recalculate_clamps_to_max():
    from app.services.threshold import recalculate_threshold

    db = AsyncMock()
    fp_result = MagicMock()
    fp_result.scalar.return_value = 5
    tp_result = MagicMock()
    tp_result.scalar.return_value = 0

    db.execute = AsyncMock(side_effect=[fp_result, tp_result])

    current = MagicMock()
    current.threshold_adjusted = 0.79
    db.get = AsyncMock(return_value=current)
    db.add = MagicMock()

    await recalculate_threshold(db, "kahn")
    assert current.threshold_adjusted == 0.80
    db.commit.assert_called_once()
