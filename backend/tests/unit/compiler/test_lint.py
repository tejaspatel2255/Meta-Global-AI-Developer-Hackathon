from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchguard.compiler.lint import LintError, lint_procedure
from benchguard.contracts.ir import Procedure

_FIXTURE = Path(__file__).resolve().parents[4] / "fixtures" / "protocols" / "protocol_b.json"


def _load() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_gold_fragment_lints_clean() -> None:
    lint_procedure(Procedure.model_validate(_load()))


def test_illegal_concept_fails() -> None:
    data = _load()
    data["objects"][0]["concept"] = "tube, rack"
    with pytest.raises(LintError) as exc:
        lint_procedure(Procedure.model_validate(data))
    assert any("illegal concept" in d or "banned" in d for d in exc.value.details)


def test_cyclic_depends_on_fails() -> None:
    data = _load()
    data["steps"][0]["depends_on"] = ["s2"]
    data["steps"][0]["index"] = 3
    with pytest.raises(LintError) as exc:
        lint_procedure(Procedure.model_validate(data))
    joined = " ".join(exc.value.details)
    assert "depends_on" in joined
