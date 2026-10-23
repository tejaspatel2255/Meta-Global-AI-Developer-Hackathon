"""Unit tests for pure BenchGuard engine lifecycle, state machine, and alarms."""

from __future__ import annotations

import json
from pathlib import Path

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import (
    AttrCategory,
    ErrorType,
    Role,
    SessionStatus,
    StepStatus,
    TickTrigger,
)
from benchguard.contracts.events import (
    AlertRaisedEvent,
    AlertResolvedEvent,
    AlertUpdatedEvent,
    ManualAppliedEvent,
    ObservationSummaryEvent,
    SessionFinishedEvent,
)
from benchguard.contracts.ir import (
    Attribute,
    ObjectDef,
    Procedure,
    Relation,
    Step,
)
from benchguard.contracts.observation import AttributeReading, Detection, Observation
from benchguard.contracts.state import ManualAction
from benchguard.engine import (
    create_initial_state,
    finish,
    manual,
    plan,
    plan_attributes,
    step,
)

_FIXTURE_PATH = Path(__file__).resolve().parents[4] / "fixtures" / "protocols" / "protocol_b.json"


def _load_protocol_b() -> Procedure:
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    return Procedure.model_validate(data)


def test_plan_concepts() -> None:
    proc = _load_protocol_b()
    state = create_initial_state(proc, "sess-1")
    req = plan(proc, state)
    # Must include "hand" and "test tube"
    assert "hand" in req.concepts
    assert "test tube" in req.concepts


def test_plan_attributes_cheap_first() -> None:
    proc = _load_protocol_b()
    state = create_initial_state(proc, "sess-1")
    tubes = [
        Detection(
            concept="test tube",
            instance_id=i,
            box=Box(x1=0.1 * i, y1=0.4, x2=0.1 * i + 0.08, y2=0.8),
            score=0.9,
        )
        for i in range(5)
    ]

    # When NOT settled: returns empty list
    queries_unsettled = plan_attributes(proc, state, tubes, settled=False)
    assert queries_unsettled == []

    # When settled: returns attribute queries for the active step's target
    queries_settled = plan_attributes(proc, state, tubes, settled=True)
    assert len(queries_settled) > 0
    assert any(q.object_id == "tube_a" for q in queries_settled)


def test_step_progression_to_done() -> None:
    proc = _load_protocol_b()
    state = create_initial_state(proc, "sess-1")
    assert state.steps[0].status == StepStatus.ACTIVE

    # Step 0 expects tube_a liquid_color to be red
    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[
            Detection(
                concept="test tube",
                instance_id=i,
                box=Box(x1=0.1 * i, y1=0.4, x2=0.1 * i + 0.08, y2=0.8),
                score=0.9,
            )
            for i in range(5)
        ],
        readings=[
            AttributeReading(
                query_id="tube_a",
                value="red",
                confidence=0.9,
                evidence="red dye",
            ),
        ],
        latency_ms={"sam": 50, "spark": 100, "total": 150},
        n_calls=2,
        errors=[],
        models={"sam": "sam-3.1", "spark": "muse-spark-1.3"},
    )

    # First tick: goals TRUE once (k_true=2 needed)
    state, events = step(proc, state, obs)
    assert state.steps[0].status == StepStatus.ACTIVE
    assert state.steps[0].consec_true == 1
    assert any(isinstance(e, ObservationSummaryEvent) for e in events)

    # Second tick: consec_true becomes 2 -> Step 0 transitions to DONE!
    obs2 = obs.model_copy(update={"tick_id": 2, "t_ms": 2000, "frame_id": "f2"})
    state, events = step(proc, state, obs2)
    assert state.steps[0].status == StepStatus.DONE
    assert state.steps[0].done_source == "engine"
    assert state.steps[0].done_at_ms == 2000
    # Step 1 should now be ACTIVE
    assert state.steps[1].status == StepStatus.ACTIVE


def test_alarm_a1_attribute_evidence() -> None:
    # A procedure where step expects red liquid
    step_def = Step(
        id="s1",
        index=1,
        instruction="Add red solution to tube",
        expects=[
            Attribute(
                object_id="tube_a",
                attribute="liquid_color",
                question="What colour?",
                allowed=["red"],
                pending=["clear"],
                category=AttrCategory.STATE,
                role=Role.GOAL,
            )
        ],
    )
    proc = Procedure(
        id="test_proto",
        title="Test",
        source={"kind": "text", "sha256": "123"},
        objects=[ObjectDef(id="tube_a", label="Tube A", concept="tube")],
        steps=[step_def],
    )
    state = create_initial_state(proc, "sess-1")

    # Observation shows blue liquid (positive evidence of mistake!)
    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[
            Detection(
                concept="tube",
                instance_id=1,
                box=Box(x1=0.2, y1=0.2, x2=0.4, y2=0.6),
                score=0.95,
            ),
        ],
        readings=[
            AttributeReading(
                query_id="tube_a",
                value="blue",
                confidence=0.88,
                evidence="bright blue",
            )
        ],
        latency_ms={},
        n_calls=1,
        errors=[],
        models={},
    )

    state, events = step(proc, state, obs)
    assert len(state.open_alerts) == 1
    alert = state.open_alerts[0]
    assert alert.error_type == ErrorType.WRONG_STATE
    assert state.steps[0].status == StepStatus.PROBLEM
    assert any(isinstance(e, AlertRaisedEvent) for e in events)


def test_alarm_a2_invariant_geometry() -> None:
    # Invariant that resistor must stay inside board
    step_def = Step(
        id="s1",
        index=1,
        instruction="Place component",
        expects=[
            Relation(
                subject_id="resistor",
                target_id="board",
                relation="inside",
                role=Role.INVARIANT,
            )
        ],
    )
    proc = Procedure(
        id="test_geo",
        title="Test",
        source={"kind": "text", "sha256": "123"},
        objects=[
            ObjectDef(id="resistor", label="Resistor", concept="resistor"),
            ObjectDef(id="board", label="Board", concept="breadboard"),
        ],
        steps=[step_def],
    )
    state = create_initial_state(proc, "sess-1")

    # Resistor is far from board (outside)
    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[
            Detection(
                concept="resistor",
                instance_id=1,
                box=Box(x1=0.8, y1=0.8, x2=0.9, y2=0.9),
                score=0.9,
            ),
            Detection(
                concept="breadboard",
                instance_id=2,
                box=Box(x1=0.1, y1=0.1, x2=0.5, y2=0.5),
                score=0.9,
            ),
        ],
        readings=[],
        latency_ms={},
        n_calls=1,
        errors=[],
        models={},
    )
    state, events = step(proc, state, obs)
    assert len(state.open_alerts) == 1
    assert state.open_alerts[0].error_type == ErrorType.WRONG_POSITION


def test_alarm_a4_wrong_order_and_reclass() -> None:
    # Protocol with 2 steps. Step 1 is active, but user performs step 2
    step1 = Step(
        id="s1",
        index=1,
        instruction="Step 1",
        expects=[
            Attribute(
                object_id="tube_1",
                attribute="liquid_color",
                question="Color?",
                allowed=["red"],
                category=AttrCategory.STATE,
                role=Role.GOAL,
            )
        ],
    )
    step2 = Step(
        id="s2",
        index=2,
        instruction="Step 2",
        expects=[
            Attribute(
                object_id="tube_2",
                attribute="liquid_color",
                question="Color?",
                allowed=["green"],
                category=AttrCategory.STATE,
                role=Role.GOAL,
            )
        ],
    )
    proc = Procedure(
        id="proto_order",
        title="Order",
        source={"kind": "text", "sha256": "123"},
        objects=[
            ObjectDef(id="tube_1", label="1", concept="tube"),
            ObjectDef(id="tube_2", label="2", concept="tube"),
        ],
        steps=[step1, step2],
    )
    state = create_initial_state(proc, "sess-1")

    # tube_1 has no reading / not satisfied, but tube_2 is already green
    obs = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[
            Detection(
                concept="tube",
                instance_id=1,
                box=Box(x1=0.1, y1=0.2, x2=0.2, y2=0.6),
                score=0.9,
            ),
            Detection(
                concept="tube",
                instance_id=2,
                box=Box(x1=0.4, y1=0.2, x2=0.5, y2=0.6),
                score=0.9,
            ),
        ],
        readings=[
            AttributeReading(
                query_id="tube_2",
                value="green",
                confidence=0.95,
                evidence="green solution",
            )
        ],
        latency_ms={},
        n_calls=1,
        errors=[],
        models={},
    )
    state, events = step(proc, state, obs)
    assert len(state.open_alerts) == 1
    assert state.open_alerts[0].error_type == ErrorType.WRONG_ORDER

    # After skip_reclass_ms (20 s) passes, the order alert reclassifies to SKIPPED_STEP
    obs_later = obs.model_copy(update={"tick_id": 2, "t_ms": 25000, "frame_id": "f2"})
    state, events2 = step(proc, state, obs_later)
    assert len(state.open_alerts) == 1
    assert state.open_alerts[0].error_type == ErrorType.SKIPPED_STEP
    assert any(isinstance(e, AlertUpdatedEvent) for e in events2)


def test_alert_resolution_when_step_done() -> None:
    step_def = Step(
        id="s1",
        index=1,
        instruction="Add liquid",
        expects=[
            Attribute(
                object_id="tube",
                attribute="liquid_color",
                question="Color?",
                allowed=["red"],
                pending=["clear"],
                category=AttrCategory.STATE,
                role=Role.GOAL,
            )
        ],
    )
    proc = Procedure(
        id="proto_res",
        title="Res",
        source={"kind": "text", "sha256": "123"},
        objects=[ObjectDef(id="tube", label="T", concept="tube")],
        steps=[step_def],
    )
    state = create_initial_state(proc, "sess-1")

    # Wrong color raised alert
    obs_wrong = Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=True,
        detections=[
            Detection(
                concept="tube",
                instance_id=1,
                box=Box(x1=0.2, y1=0.2, x2=0.4, y2=0.6),
                score=0.9,
            )
        ],
        readings=[
            AttributeReading(
                query_id="tube",
                value="blue",
                confidence=0.9,
                evidence="blue",
            )
        ],
        latency_ms={},
        n_calls=1,
        errors=[],
        models={},
    )
    state, _ = step(proc, state, obs_wrong)
    assert len(state.open_alerts) == 1

    # User manually marks step done
    state, events = manual(proc, state, ManualAction(step_id="s1", action="done"), t_ms=2000)
    assert state.steps[0].status == StepStatus.DONE
    assert len(state.open_alerts) == 0
    assert any(isinstance(e, AlertResolvedEvent) for e in events)
    assert any(isinstance(e, ManualAppliedEvent) for e in events)


def test_finish_summary() -> None:
    proc = _load_protocol_b()
    state = create_initial_state(proc, "sess-1")
    state, events = finish(proc, state, t_ms=5000)
    assert state.status == SessionStatus.FINISHED
    assert len(events) == 1
    assert isinstance(events[0], SessionFinishedEvent)
    assert events[0].summary["s1"] == "INCOMPLETE"
