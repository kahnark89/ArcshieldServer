"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    op.create_table(
        "events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operator_id", sa.Text, nullable=False),
        sa.Column("shift_phase", sa.Text),
        sa.Column("material_batch_id", sa.Text),
        sa.Column("ambient_temp_f", sa.Float),
        sa.Column("trigger_type", sa.Text, nullable=False),
        sa.Column("operational_mode", sa.Text),
        sa.Column("confidence_score", sa.Float),
        sa.Column("gaze_score", sa.Float),
        sa.Column("hand_score", sa.Float),
        sa.Column("hrv_score", sa.Float),
        sa.Column("acoustic_score", sa.Float),
        sa.Column("srk_level", sa.Text),
        sa.Column("hypothesis_confirmed", sa.Boolean),
        sa.Column("outcome_tag", sa.Text),
        sa.Column("graph_weight", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("withhold_sample", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("operator_validated", sa.Boolean),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("event_json", postgresql.JSONB, nullable=False),
        sa.Column(sa.Column("cause_embedding", sa.Text).key, sa.Text),
    )

    op.execute("ALTER TABLE events DROP COLUMN cause_embedding")
    op.execute("ALTER TABLE events ADD COLUMN cause_embedding vector(384)")

    op.create_index("events_operator_created", "events", ["operator_id", "created_at"])
    op.create_index("events_outcome", "events", ["outcome_tag"])
    op.execute(
        "CREATE INDEX events_validated ON events (operator_validated) "
        "WHERE operator_validated IS NOT NULL"
    )

    op.create_table(
        "sensor_streams",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.event_id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_name", sa.Text, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
    )
    op.execute("SELECT create_hypertable('sensor_streams', 'ts')")
    op.create_index("sensor_event_signal", "sensor_streams", ["event_id", "signal_name", "ts"])

    op.create_table(
        "threshold_history",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("operator_id", sa.Text, nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=False),
        sa.Column("direction", sa.Text),
        sa.Column("fp_rate_hourly", sa.Float),
        sa.Column("tp_count_hourly", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "current_thresholds",
        sa.Column("operator_id", sa.Text, primary_key=True),
        sa.Column("threshold_immediate", sa.Float, nullable=False, server_default="0.75"),
        sa.Column("threshold_counter", sa.Float, nullable=False, server_default="0.60"),
        sa.Column("threshold_adjusted", sa.Float, nullable=False, server_default="0.65"),
        sa.Column("mode", sa.Text, nullable=False, server_default="'STEADY'"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("current_thresholds")
    op.drop_table("threshold_history")
    op.drop_index("sensor_event_signal", table_name="sensor_streams")
    op.drop_table("sensor_streams")
    op.drop_index("events_validated", table_name="events")
    op.drop_index("events_outcome", table_name="events")
    op.drop_index("events_operator_created", table_name="events")
    op.drop_table("events")
