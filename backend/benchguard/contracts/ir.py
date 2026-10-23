"""Procedure IR — docs/CONTRACTS.md §2."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from benchguard.contracts.enums import AttrCategory, ErrorType, Role


class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    axis: Literal["x", "y"]
    index: int = Field(ge=0)
    of: int = Field(ge=1)


class ObjectDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    concept: str
    expected_count: int | None = None
    slot: Slot | None = None


class PredBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role = Role.GOAL
    note: str | None = None


class Present(PredBase):
    kind: Literal["present"] = "present"
    object_id: str
    min_count: int = 1
    max_count: int | None = None


class Absent(PredBase):
    kind: Literal["absent"] = "absent"
    object_id: str


class Relation(PredBase):
    kind: Literal["relation"] = "relation"
    subject_id: str
    relation: Literal[
        "left_of",
        "right_of",
        "above",
        "below",
        "inside",
        "overlaps",
        "near",
    ]
    target_id: str
    negate: bool = False


class OrderAlong(PredBase):
    kind: Literal["order_along"] = "order_along"
    object_ids: list[str]
    axis: Literal["x", "y"]


class Confirm(PredBase):
    kind: Literal["confirm"] = "confirm"
    prompt: str


GatePredicate = Annotated[
    Present | Absent | Relation | OrderAlong,
    Field(discriminator="kind"),
]


class Attribute(PredBase):
    kind: Literal["attribute"] = "attribute"
    object_id: str
    attribute: str
    question: str
    allowed: list[str]
    pending: list[str] = Field(default_factory=list)
    category: AttrCategory
    gate: GatePredicate | None = None


Predicate = Annotated[
    Present | Absent | Relation | OrderAlong | Attribute | Confirm,
    Field(discriminator="kind"),
]


class ErrorSignature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: ErrorType
    when: list[Predicate]
    message_hint: str = ""


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    index: int
    instruction: str
    expects: list[Predicate]
    errors: list[ErrorSignature] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    persistent: bool = False
    hints: dict[ErrorType, str] = Field(default_factory=dict)


class Procedure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    id: str
    title: str
    source: dict[str, Any]
    objects: list[ObjectDef]
    steps: list[Step]
    compile_meta: dict[str, Any] = Field(default_factory=dict)
