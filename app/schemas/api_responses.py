from typing import Optional
from pydantic import BaseModel


class EventIngestResponse(BaseModel):
    event_id: str
    status: str


class EventSummary(BaseModel):
    event_id: str
    operator_id: str
    trigger_type: str
    outcome_tag: Optional[str]
    graph_weight: float
    operator_validated: Optional[bool]
    shift_phase: Optional[str]
    srk_level: Optional[str]
    created_at: str


class EventListResponse(BaseModel):
    total: int
    page: int
    limit: int
    results: list[EventSummary]


class TwinQueryResult(BaseModel):
    event_id: str
    cause_description: str
    intuition_hypothesis: str
    action_description: str
    outcome_tag: Optional[str]
    graph_weight: float
    similarity_score: float


class TwinQueryResponse(BaseModel):
    results: list[TwinQueryResult]


class ThresholdResponse(BaseModel):
    threshold_immediate: float
    threshold_counter: float
    threshold_adjusted: float
    mode: str


class FeedbackUpdateResponse(BaseModel):
    event_id: str
    status: str


class ThresholdHistoryEntry(BaseModel):
    threshold_value: float
    direction: Optional[str]
    fp_rate_hourly: Optional[float]
    tp_count_hourly: Optional[int]
    created_at: str


class ThresholdHistoryResponse(BaseModel):
    operator_id: str
    entries: list[ThresholdHistoryEntry]
