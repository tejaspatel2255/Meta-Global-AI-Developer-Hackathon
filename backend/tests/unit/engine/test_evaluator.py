"""Unit tests for pure predicate evaluation — docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import AttrCategory, PredicateStatus, TickTrigger
from benchguard.contracts.ir import (
    Absent,
    Attribute,
    Confirm,
    ObjectDef,
    OrderAlong,
    Present,
    Relation,
    Slot,
)
from benchguard.contracts.observation import AttributeReading, Detection, Observation
from benchguard.engine.config import EngineConfig
from benchguard.engine.evaluator import evaluate_predicate
from benchguard.geometry.resolution import resolve_scene


def _make_dummy_obs(
    readings: list[AttributeReading] | None = None,
    detections: list[Detection] | None = None,
    settled: bool = True,
) -> Observation:
    return Observation(
        tick_id=1,
        t_ms=1000,
        frame_id="f1",
        trigger=TickTrigger.CHANGE,
        settled=settled,
        detections=detections or [],
        readings=readings or [],
        latency_ms={"sam": 100, "spark": 150, "total": 250},
        n_calls=2,
        errors=[],
        models={"sam": "sam-3.1", "spark": "muse-spark-1.3"},
    )


def test_eval_present_and_absent() -> None:
    cfg = EngineConfig()
    objects = [
        ObjectDef(id="resistor_1", label="Resistor", concept="resistor"),
        ObjectDef(id="led_1", label="LED", concept="led"),
    ]
    detections = [
        Detection(
            concept="resistor",
            instance_id=1,
            box=Box(x1=0.1, y1=0.1, x2=0.3, y2=0.3),
            score=0.9,
        ),
    ]
    scene = resolve_scene(objects, detections, cfg.det_score_min, cfg.occlusion_overlap)
    obs = _make_dummy_obs(detections=detections)

    # Present resistor -> TRUE
    res_pres = evaluate_predicate(
        Present(object_id="resistor_1"),
        "s1",
        0,
        obs,
        scene,
        cfg,
    )
    assert res_pres.status == PredicateStatus.TRUE
    assert res_pres.confidence == 0.9

    # Present led -> FALSE (count 0 < 1)
    led_pres = evaluate_predicate(
        Present(object_id="led_1"),
        "s1",
        1,
        obs,
        scene,
        cfg,
    )
    assert led_pres.status == PredicateStatus.FALSE
    assert led_pres.confidence == cfg.absence_conf

    # Absent led -> TRUE
    led_abs = evaluate_predicate(
        Absent(object_id="led_1"),
        "s1",
        2,
        obs,
        scene,
        cfg,
    )
    assert led_abs.status == PredicateStatus.TRUE


def test_eval_relation() -> None:
    cfg = EngineConfig()
    objects = [
        ObjectDef(id="led", label="LED", concept="led"),
        ObjectDef(id="board", label="Breadboard", concept="breadboard"),
    ]
    detections = [
        Detection(
            concept="led",
            instance_id=1,
            box=Box(x1=0.2, y1=0.2, x2=0.3, y2=0.3),
            score=0.95,
        ),
        Detection(
            concept="breadboard",
            instance_id=2,
            box=Box(x1=0.1, y1=0.1, x2=0.6, y2=0.6),
            score=0.98,
        ),
    ]
    scene = resolve_scene(objects, detections, cfg.det_score_min, cfg.occlusion_overlap)
    obs = _make_dummy_obs(detections=detections)

    # inside relation holds
    res = evaluate_predicate(
        Relation(subject_id="led", target_id="board", relation="inside"),
        "s1",
        0,
        obs,
        scene,
        cfg,
    )
    assert res.status == PredicateStatus.TRUE
    assert res.confidence == 0.95


def test_eval_order_along() -> None:
    cfg = EngineConfig()
    objects = [
        ObjectDef(
            id="tube_a",
            label="A",
            concept="test tube",
            slot=Slot(axis="x", index=0, of=2),
        ),
        ObjectDef(
            id="tube_b",
            label="B",
            concept="test tube",
            slot=Slot(axis="x", index=1, of=2),
        ),
    ]
    detections = [
        Detection(
            concept="test tube",
            instance_id=1,
            box=Box(x1=0.1, y1=0.4, x2=0.2, y2=0.8),
            score=0.9,
        ),
        Detection(
            concept="test tube",
            instance_id=2,
            box=Box(x1=0.5, y1=0.4, x2=0.6, y2=0.8),
            score=0.9,
        ),
    ]
    scene = resolve_scene(objects, detections, cfg.det_score_min, cfg.occlusion_overlap)
    obs = _make_dummy_obs(detections=detections)

    res = evaluate_predicate(
        OrderAlong(object_ids=["tube_a", "tube_b"], axis="x"),
        "s1",
        0,
        obs,
        scene,
        cfg,
    )
    assert res.status == PredicateStatus.TRUE


def test_eval_attribute_tri_state() -> None:
    cfg = EngineConfig()
    objects = [ObjectDef(id="tube_d", label="Tube D", concept="test tube")]
    detections = [
        Detection(
            concept="test tube",
            instance_id=1,
            box=Box(x1=0.3, y1=0.4, x2=0.4, y2=0.8),
            score=0.9,
        ),
    ]
    scene = resolve_scene(objects, detections, cfg.det_score_min, cfg.occlusion_overlap)

    attr_pred = Attribute(
        object_id="tube_d",
        attribute="liquid_color",
        question="What color is the liquid?",
        allowed=["red"],
        pending=["clear"],
        category=AttrCategory.STATE,
    )

    # 1. Allowed reading -> TRUE
    obs_allowed = _make_dummy_obs(
        readings=[
            AttributeReading(
                query_id="tube_d",
                value="red",
                confidence=0.88,
                evidence="clear red liquid",
            )
        ]
    )
    res_allowed = evaluate_predicate(attr_pred, "s2", 0, obs_allowed, scene, cfg)
    assert res_allowed.status == PredicateStatus.TRUE

    # 2. Pending reading -> FALSE with benign=True (no alarm)
    obs_pending = _make_dummy_obs(
        readings=[
            AttributeReading(
                query_id="tube_d",
                value="clear",
                confidence=0.91,
                evidence="transparent water",
            )
        ]
    )
    res_pending = evaluate_predicate(attr_pred, "s2", 0, obs_pending, scene, cfg)
    assert res_pending.status == PredicateStatus.FALSE
    assert res_pending.benign is True
    assert res_pending.reason == "PENDING_VALUE"

    # 3. Unallowed reading with high conf -> FALSE with benign=False, reason=EVIDENCE
    obs_evidence = _make_dummy_obs(
        readings=[
            AttributeReading(
                query_id="tube_d",
                value="blue",
                confidence=0.85,
                evidence="dark blue solution",
            )
        ]
    )
    res_evidence = evaluate_predicate(attr_pred, "s2", 0, obs_evidence, scene, cfg)
    assert res_evidence.status == PredicateStatus.FALSE
    assert res_evidence.benign is False
    assert res_evidence.reason == "EVIDENCE"


def test_eval_confirm() -> None:
    cfg = EngineConfig()
    objects: list[ObjectDef] = []
    scene = resolve_scene(objects, [], cfg.det_score_min, cfg.occlusion_overlap)
    obs = _make_dummy_obs()

    pred = Confirm(prompt="Did you attach the jumper wire?")
    unconfirmed = evaluate_predicate(pred, "s1", 0, obs, scene, cfg)
    assert unconfirmed.status == PredicateStatus.UNKNOWN

    confirmed = evaluate_predicate(
        pred, "s1", 0, obs, scene, cfg, confirmed_prompts={"Did you attach the jumper wire?"}
    )
    assert confirmed.status == PredicateStatus.TRUE
