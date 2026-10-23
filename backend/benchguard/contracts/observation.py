"""Perception and observation contracts — docs/CONTRACTS.md §3."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import TickTrigger


class Detection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    instance_id: int
    box: Box
    score: float | None = None
    mask_svg: str | None = None


class PerceptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[str]


class AttributeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    object_id: str
    attribute: str
    question: str
    allowed_values: list[str]
    box: Box


class AttributeReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    value: str
    confidence: float
    evidence: str = Field(max_length=160)


class ModelError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    kind: Literal["timeout", "rate_limit", "http", "parse", "budget"]
    detail: str


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_id: int
    t_ms: int
    frame_id: str
    trigger: TickTrigger
    settled: bool
    detections: list[Detection]
    readings: list[AttributeReading]
    latency_ms: dict[str, int]
    n_calls: int
    errors: list[ModelError] = Field(default_factory=list)
    models: dict[str, str]
