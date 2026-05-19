from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class AcousticBaseline(BaseModel):
    spectral_centroid_hz: float
    dominant_freq_hz: float
    amplitude_dbfs: float
    freq_histogram: list[float] = Field(default_factory=list)


class VibrationBaseline(BaseModel):
    dominant_freq_hz: float
    rms_acceleration: float
    peak_acceleration: float
    freq_histogram: list[float] = Field(default_factory=list)


class VisualBaseline(BaseModel):
    motion_score: float
    luminance: float
    frame_path: Optional[str] = None
    capture_mode: str = ""


class OlfactoryBaseline(BaseModel):
    annotation: Optional[str] = None
    intensity: Optional[int] = None
    voc_ppb: Optional[float] = None
    wake_word_triggered: bool = False


class ThermalBaseline(BaseModel):
    ambient_temp_f: Optional[float] = None
    source_label: str = ""


class SensoryBaseline(BaseModel):
    acoustic: Optional[AcousticBaseline] = None
    vibration: Optional[VibrationBaseline] = None
    visual: Optional[VisualBaseline] = None
    olfactory: Optional[OlfactoryBaseline] = None
    thermal: Optional[ThermalBaseline] = None


class PreEnv(BaseModel):
    operator_id: str
    shift_phase: Optional[str] = None
    material_batch_id: Optional[str] = None
    ambient_temp_f: Optional[float] = None
    recent_events_summary: Optional[str] = None
    sensory_baseline: Optional[SensoryBaseline] = None


class SignalScores(BaseModel):
    gaze: Optional[float] = None
    hand: Optional[float] = None
    hrv: Optional[float] = None
    acoustic: Optional[float] = None


class SensorContext(BaseModel):
    pass

    model_config = {"extra": "allow"}


class Feedback(BaseModel):
    operator_validated: Optional[bool] = None
    notes: Optional[str] = None


class TriggerContext(BaseModel):
    signal_scores: Optional[SignalScores] = None
    temporal_modifier: Optional[float] = None
    operational_mode: Optional[str] = None
    sensor_context: Optional[SensorContext] = None
    feedback: Optional[Feedback] = None


class Cause(BaseModel):
    description: str
    trigger_type: str
    trigger_channels: list[str] = Field(default_factory=list)
    trigger_context: Optional[TriggerContext] = None
    timestamp: str


class Intuition(BaseModel):
    srk_level: str
    hypothesis: str
    hypothesis_confirmed: Optional[bool] = None
    confidence: Optional[float] = None


class Action(BaseModel):
    description: str
    tool_used: Optional[str] = None


class ShadowAction(BaseModel):
    description: str
    rejection_rationale: str
    srk_level: str


class Effect(BaseModel):
    observed_outcome: str
    timestamp: Optional[str] = None


class Result(BaseModel):
    outcome_tag: str
    notes: Optional[str] = None
    graph_weight: float = 0.5
    withhold_sample: bool = False


class BiometricSnapshot(BaseModel):
    hr_bpm: Optional[int] = None
    hrv_rmssd_ms: Optional[float] = None
    skin_temp_c: Optional[float] = None
    source_device: Optional[str] = None


class CaptureDevice(BaseModel):
    model_config = {"extra": "allow"}


class CiaerPlusEvent(BaseModel):
    event_id: str
    capture_device: Optional[CaptureDevice] = None
    pre_env: PreEnv
    cause: Cause
    intuition: Intuition
    action: Action
    shadow_actions: list[ShadowAction] = Field(default_factory=list)
    effect: Effect
    result: Result
    biometric_snapshot: Optional[BiometricSnapshot] = None
