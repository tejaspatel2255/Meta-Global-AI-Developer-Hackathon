"""Unit tests for benchguard.compiler package."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from benchguard.compiler import (
    CompileError,
    build_compile_messages,
    compile_sop,
    compile_sop_sync,
    get_procedure_json_schema,
    lint_procedure,
)
from benchguard.contracts.ir import Procedure

_PROTOCOLS_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "protocols"


class MockModelClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.call_count = 0
        self.received_messages: list[list[dict[str, str]]] = []

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        model: str = "muse-spark-1.3",
        temperature: float = 0.1,
    ) -> str:
        self.call_count += 1
        self.received_messages.append(messages)
        if not self._responses:
            msg = "No more mock responses configured"
            raise RuntimeError(msg)
        return self._responses.pop(0)


def test_schema_valid() -> None:
    schema = get_procedure_json_schema()
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "objects" in schema["properties"]
    assert "steps" in schema["properties"]


def test_prompt_construction() -> None:
    messages = build_compile_messages("1. Insert resistor.\n2. Insert LED.")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "BenchGuard Procedure IR Compiler" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "<sop>" in messages[1]["content"]
    assert "1. Insert resistor." in messages[1]["content"]


@pytest.mark.asyncio
async def test_compile_input_validation() -> None:
    with pytest.raises(CompileError, match="EMPTY_INPUT"):
        await compile_sop("   ")

    with pytest.raises(CompileError, match="INPUT_TOO_LONG"):
        await compile_sop("x" * 20001)


@pytest.mark.asyncio
async def test_compile_success_first_attempt() -> None:
    gold_b = json.loads((_PROTOCOLS_DIR / "protocol_b.json").read_text(encoding="utf-8"))
    client = MockModelClient([json.dumps(gold_b)])

    sop_text = (_PROTOCOLS_DIR / "protocol_b.sop.txt").read_text(encoding="utf-8")
    proc, warnings = await compile_sop(sop_text, client=client)

    assert proc.id == "protocol_b"
    assert len(proc.objects) == 5
    assert proc.compile_meta["attempts"] == 1
    assert warnings == []
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_compile_retry_on_lint_failure_then_success() -> None:
    gold_b = json.loads((_PROTOCOLS_DIR / "protocol_b.json").read_text(encoding="utf-8"))

    # Attempt 1 has an illegal concept with comma
    bad_data = copy.deepcopy(gold_b)
    bad_data["objects"][0]["concept"] = "tube, rack"

    # Attempt 2 is valid
    good_data = copy.deepcopy(gold_b)

    client = MockModelClient([json.dumps(bad_data), json.dumps(good_data)])
    sop_text = (_PROTOCOLS_DIR / "protocol_b.sop.txt").read_text(encoding="utf-8")

    proc, warnings = await compile_sop(sop_text, client=client, max_attempts=3)
    assert proc.id == "protocol_b"
    assert proc.compile_meta["attempts"] == 2
    assert client.call_count == 2

    # Check that retry message included lint details
    second_call_messages = client.received_messages[1]
    assert len(second_call_messages) == 4  # system, user, assistant(bad), user(retry)
    retry_content = second_call_messages[-1]["content"]
    assert "illegal concept" in retry_content or "banned punctuation" in retry_content


@pytest.mark.asyncio
async def test_compile_exhausts_attempts() -> None:
    # 3 bad responses with invalid JSON
    client = MockModelClient(["not a json", "still not json", "definitely not json"])
    with pytest.raises(CompileError, match="COMPILE_FAILED"):
        await compile_sop("Sample SOP", client=client, max_attempts=3)
    assert client.call_count == 3


def test_compile_sync_wrapper() -> None:
    gold_b = json.loads((_PROTOCOLS_DIR / "protocol_b.json").read_text(encoding="utf-8"))
    client = MockModelClient([json.dumps(gold_b)])
    proc, _ = compile_sop_sync("Sample SOP", client=client)
    assert proc.id == "protocol_b"


def test_gold_protocols_validate_and_lint() -> None:
    for proto_file in ["protocol_a.json", "protocol_b.json"]:
        path = _PROTOCOLS_DIR / proto_file
        data = json.loads(path.read_text(encoding="utf-8"))
        proc = Procedure.model_validate(data)
        lint_procedure(proc)
        assert len(proc.objects) > 0
        assert len(proc.steps) > 0

    for sop_file in ["protocol_a.sop.txt", "protocol_b.sop.txt"]:
        path = _PROTOCOLS_DIR / sop_file
        assert path.is_file()
        assert len(path.read_text(encoding="utf-8").strip()) > 0
