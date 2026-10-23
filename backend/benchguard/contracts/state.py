"""Engine state — docs/CONTRACTS.md §4."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from benchguard.contracts.enums import (
    ErrorType,
    PredicateStatus,
    SessionStatus,
    StepStatus,
)


class PredicateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    index: int
    status: PredicateStatus
    confidence: float
    reason: str
    benign: bool = False


class StepState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    status: StepStatus
    satisfied_early: bool = False
    consec_true: int = 0
    consec_evidence: int = 0
    unknown_since_ms: int | None = None
    done_at_ms: int | None = None
    done_source: Literal["engine", "manual"] | None = None


class Alert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    t_ms: int
    step_id: str
    related_step_id: str | None = None
    error_type: ErrorType
    message: str
    confidence: float
    evidence_frame_ids: list[str]
    evidence_tick_ids: list[int]
    resolved_at_ms: int | None = None
    resolution: str | None = None


class SessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    procedure_id: str
    status: SessionStatus
    steps: list[StepState]
    open_alerts: list[Alert] = Field(default_factory=list)
    seq: int = 0
    tick_id: int = 0
    n_calls: int = 0
    cooldowns: dict[str, int] = Field(default_factory=dict)
    counters: dict[str, int] = Field(default_factory=dict)


class ManualAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    action: Literal["done", "skip", "confirm"]
