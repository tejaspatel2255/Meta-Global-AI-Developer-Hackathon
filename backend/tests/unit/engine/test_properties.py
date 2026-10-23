"""Property-based tests for pure engine determinism and invariants — docs/ARCHITECTURE.md §6.5."""

from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import (
    StepStatus,
    TickTrigger,
)
from benchguard.contracts.ir import (
    Procedure,
)
from benchguard.contracts.observation import AttributeReading, Detection, Observation
from benchguard.engine import create_initial_state, step

_FIXTURE_PATH = Path(__file__).resolve().parents[4] / "fixtures" / "protocols" / "protocol_b.json"


def _load_proto() -> Procedure:
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return Procedure.model_validate(data)


@given(
    settled=st.booleans(),
    confidence=st.floats(min_value=0.1, max_value=0.99),
    color=st.sampled_from(["red", "clear", "blue", "green", "unclear"]),
)
def test_engine_determinism(settled: bool, confidence: float, color: str) -> None:
    """Same inputs to step() must produce strictly identical (state, events)."""
    proc = _load_proto()
    state = create_initial_state(proc, "sess-det")

    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=settled,
        detections=[
            Detection(
                concept="test tube",
                instance_id=i,
                box=Box(x1=0.1 * i, y1=0.3, x2=0.1 * i + 0.08, y2=0.8),
                score=0.9,
            )
            for i in range(5)
        ],
        readings=[
            AttributeReading(
                query_id="tube_b",
                value=color,
                confidence=confidence,
                evidence=f"observed {color}",
            )
        ],
        latency_ms={"sam": 50, "spark": 100, "total": 150},
        n_calls=1,
        errors=[],
        models={"sam": "sam-3.1", "spark": "muse-spark-1.3"},
    )

    state1, events1 = step(proc, state, obs)
    state2, events2 = step(proc, state, obs)

    assert state1.model_dump() == state2.model_dump()
    assert [e.model_dump() for e in events1] == [e.model_dump() for e in events2]


@given(
    color=st.sampled_from(["blue", "yellow", "black"]),
    confidence=st.floats(min_value=0.7, max_value=0.99),
)
def test_no_alert_when_unsettled(color: str, confidence: float) -> None:
    """R4: Even if wrong visual evidence is observed, unsettled scene NEVER raises alerts."""
    proc = _load_proto()
    state = create_initial_state(proc, "sess-unsettled")

    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=False,  # Moving scene!
        detections=[
            Detection(
                concept="test tube",
                instance_id=i,
                box=Box(x1=0.1 * i, y1=0.3, x2=0.1 * i + 0.08, y2=0.8),
                score=0.9,
            )
            for i in range(5)
        ],
        readings=[
            AttributeReading(
                query_id="tube_b",
                value=color,
                confidence=confidence,
                evidence=f"observed {color}",
            )
        ],
        latency_ms={},
        n_calls=1,
        errors=[],
        models={},
    )

    new_state, _ = step(proc, state, obs)
    assert len(new_state.open_alerts) == 0


def test_no_alert_on_absence_or_unknown() -> None:
    """R4: Absence of objects or unknown status NEVER raises red alert."""
    proc = _load_proto()
    state = create_initial_state(proc, "sess-empty")

    # Empty scene: zero detections, zero readings, but settled
    obs_empty = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[],
        readings=[],
        latency_ms={},
        n_calls=0,
        errors=[],
        models={},
    )

    new_state, _ = step(proc, state, obs_empty)
    assert len(new_state.open_alerts) == 0
    assert new_state.steps[0].status in {StepStatus.ACTIVE, StepStatus.UNCERTAIN}
