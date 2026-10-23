"""Normalized bounding box [x1,y1,x2,y2], top-left origin."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Box(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "Box":
        if self.x2 < self.x1 or self.y2 < self.y1:
            msg = "box must have x2>=x1 and y2>=y1"
            raise ValueError(msg)
        return self
