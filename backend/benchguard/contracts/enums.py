"""Shared enumerations — source of truth with docs/CONTRACTS.md §1."""

from enum import StrEnum


class PredicateStatus(StrEnum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DONE = "DONE"
    UNCERTAIN = "UNCERTAIN"
    PROBLEM = "PROBLEM"


class ErrorType(StrEnum):
    """Precedence is declaration order (MISSING_OBJECT is preflight/finish only)."""

    WRONG_ORDER = "WRONG_ORDER"
    SKIPPED_STEP = "SKIPPED_STEP"
    REGRESSION = "REGRESSION"
    WRONG_POSITION = "WRONG_POSITION"
    WRONG_ORIENTATION = "WRONG_ORIENTATION"
    WRONG_OBJECT = "WRONG_OBJECT"
    WRONG_STATE = "WRONG_STATE"
    MISSING_OBJECT = "MISSING_OBJECT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class Role(StrEnum):
    GOAL = "goal"
    INVARIANT = "invariant"


class AttrCategory(StrEnum):
    ORIENTATION = "orientation"
    STATE = "state"
    IDENTITY = "identity"


class TickTrigger(StrEnum):
    CHANGE = "change"
    MANUAL = "manual"
    HEARTBEAT = "heartbeat"
    PREFLIGHT = "preflight"


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    PREFLIGHT = "PREFLIGHT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    PAUSED_BUDGET = "PAUSED_BUDGET"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
