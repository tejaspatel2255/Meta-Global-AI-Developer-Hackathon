from __future__ import annotations

import json
from pathlib import Path

from benchguard.contracts.ir import Procedure

_FIXTURE = Path(__file__).resolve().parents[4] / "fixtures" / "protocols" / "protocol_b.json"


def test_protocol_b_fixture_validates() -> None:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    proc = Procedure.model_validate(data)
    assert proc.id == "protocol_b"
    assert len(proc.objects) == 5
    assert proc.steps[1].id == "s2"
    roundtrip = Procedure.model_validate(proc.model_dump())
    assert roundtrip == proc
