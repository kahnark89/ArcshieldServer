from datetime import datetime
from sqlalchemy import Text, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ThresholdHistory(Base):
    __tablename__ = "threshold_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str | None] = mapped_column(Text)
    fp_rate_hourly: Mapped[float | None] = mapped_column(Float)
    tp_count_hourly: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class CurrentThreshold(Base):
    __tablename__ = "current_thresholds"

    operator_id: Mapped[str] = mapped_column(Text, primary_key=True)
    threshold_immediate: Mapped[float] = mapped_column(Float, default=0.75)
    threshold_counter: Mapped[float] = mapped_column(Float, default=0.60)
    threshold_adjusted: Mapped[float] = mapped_column(Float, default=0.65)
    mode: Mapped[str] = mapped_column(Text, default="STEADY")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
