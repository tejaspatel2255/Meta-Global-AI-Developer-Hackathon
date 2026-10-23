"""JSON schema exporter for Spark structured output — docs/ARCHITECTURE.md §8."""

from __future__ import annotations

from typing import Any

from benchguard.contracts.ir import Procedure


def get_procedure_json_schema() -> dict[str, Any]:
    """Return the JSON schema for Procedure IR."""
    return Procedure.model_json_schema()


def get_response_format() -> dict[str, Any]:
    """Return Chat Completions response_format payload for Procedure."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "Procedure",
            "schema": get_procedure_json_schema(),
            "strict": False,
        },
    }
