import uuid
from datetime import datetime
from sqlalchemy import Text, Boolean, Float, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from app.database import Base


class Event(Base):
    __tablename__ = "events"

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    operator_id: Mapped[str] = mapped_column(Text, nullable=False)
    shift_phase: Mapped[str | None] = mapped_column(Text)
    material_batch_id: Mapped[str | None] = mapped_column(Text)
    ambient_temp_f: Mapped[float | None] = mapped_column(Float)
    trigger_type: Mapped[str] = mapped_column(Text, nullable=False)
    operational_mode: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    gaze_score: Mapped[float | None] = mapped_column(Float)
    hand_score: Mapped[float | None] = mapped_column(Float)
    hrv_score: Mapped[float | None] = mapped_column(Float)
    acoustic_score: Mapped[float | None] = mapped_column(Float)
    srk_level: Mapped[str | None] = mapped_column(Text)
    hypothesis_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    outcome_tag: Mapped[str | None] = mapped_column(Text)
    graph_weight: Mapped[float] = mapped_column(Float, default=0.5)
    withhold_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    operator_validated: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    event_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cause_embedding: Mapped[list[float] | None] = mapped_column(Vector(384))

    __table_args__ = (
        Index("events_operator_created", "operator_id", "created_at"),
        Index("events_outcome", "outcome_tag"),
        Index(
            "events_validated",
            "operator_validated",
            postgresql_where="operator_validated IS NOT NULL",
        ),
    )
