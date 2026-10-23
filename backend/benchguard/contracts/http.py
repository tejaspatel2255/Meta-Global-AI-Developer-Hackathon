"""REST request/response envelopes — docs/CONTRACTS.md §5."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from benchguard.contracts.ir import Procedure


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    version: str


class ModelsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sam: bool
    spark: bool


class CompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sop_text: str = Field(max_length=20_000)


class CompileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    procedure: Procedure
    warnings: list[str] = Field(default_factory=list)


class ApiErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: Any | None = None


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ApiErrorBody
