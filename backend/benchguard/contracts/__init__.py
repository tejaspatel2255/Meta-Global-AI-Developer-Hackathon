"""Pydantic contracts (source of truth)."""

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import (
    AttrCategory,
    ErrorType,
    PredicateStatus,
    Role,
    SessionStatus,
    StepStatus,
    TickTrigger,
)
from benchguard.contracts.events import Event, PreflightResult
from benchguard.contracts.http import CompileRequest, HealthResponse, ModelsResponse
from benchguard.contracts.ir import (
    Attribute,
    ObjectDef,
    Predicate,
    Procedure,
    Step,
)
from benchguard.contracts.observation import Observation
from benchguard.contracts.state import Alert, ManualAction, SessionState, StepState

__all__ = [
    "Alert",
    "AttrCategory",
    "Attribute",
    "Box",
    "CompileRequest",
    "ErrorType",
    "Event",
    "HealthResponse",
    "ManualAction",
    "ModelsResponse",
    "ObjectDef",
    "Observation",
    "Predicate",
    "PredicateStatus",
    "PreflightResult",
    "Procedure",
    "Role",
    "SessionState",
    "SessionStatus",
    "Step",
    "StepState",
    "StepStatus",
    "TickTrigger",
]
