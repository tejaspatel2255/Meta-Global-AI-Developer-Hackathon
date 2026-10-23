"""WebSocket / JSONL events — docs/CONTRACTS.md §4."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import SessionStatus, StepStatus
from benchguard.contracts.state import Alert, PredicateResult, StepState


class EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int
    t_ms: int


class OverlayBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    box: Box
    score: float | None = None


class PreflightObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str
    concept: str
    found: int
    expected: int | None
    ok: bool
    suggestion: str | None = None


class PreflightResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objects: list[PreflightObject]
    blur_score: float
    brightness: float
    quality_ok: bool
    goal_true_at_start: list[str]
    models_ok: dict[str, bool]


class SessionStatusEvent(EventBase):
    type: Literal["session.status"] = "session.status"
    status: SessionStatus
    detail: str | None = None


class PreflightResultEvent(EventBase):
    type: Literal["preflight.result"] = "preflight.result"
    result: PreflightResult


class ObservationSummaryEvent(EventBase):
    type: Literal["observation.summary"] = "observation.summary"
    tick_id: int
    trigger: str
    settled: bool
    n_detections: int
    latency_ms: dict[str, int]
    degraded: bool
    overlay: list[OverlayBox] = Field(default_factory=list)


class StepUpdatedEvent(EventBase):
    type: Literal["step.updated"] = "step.updated"
    step: StepState
    last_results: list[PredicateResult]


class AlertRaisedEvent(EventBase):
    type: Literal["alert.raised"] = "alert.raised"
    alert: Alert


class AlertUpdatedEvent(EventBase):
    type: Literal["alert.updated"] = "alert.updated"
    alert: Alert


class AlertResolvedEvent(EventBase):
    type: Literal["alert.resolved"] = "alert.resolved"
    alert: Alert


class ManualAppliedEvent(EventBase):
    type: Literal["manual.applied"] = "manual.applied"
    step_id: str
    action: str


class SessionFinishedEvent(EventBase):
    type: Literal["session.finished"] = "session.finished"
    summary: dict[str, StepStatus | Literal["INCOMPLETE"]]
    report_urls: dict[str, str] = Field(default_factory=dict)


class ErrorEvent(EventBase):
    type: Literal["error"] = "error"
    code: str
    message: str
    fatal: bool


Event = Annotated[
    SessionStatusEvent
    | PreflightResultEvent
    | ObservationSummaryEvent
    | StepUpdatedEvent
    | AlertRaisedEvent
    | AlertUpdatedEvent
    | AlertResolvedEvent
    | ManualAppliedEvent
    | SessionFinishedEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
