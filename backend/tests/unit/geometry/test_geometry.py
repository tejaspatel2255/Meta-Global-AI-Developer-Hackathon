"""Unit tests for benchguard.geometry package."""

from __future__ import annotations

import pytest

from benchguard.contracts.boxes import Box
from benchguard.contracts.ir import ObjectDef, Slot
from benchguard.contracts.observation import Detection
from benchguard.geometry import (
    above,
    area,
    below,
    center,
    check_relation,
    crop_box,
    inside,
    intersection,
    intersection_area,
    iou,
    left_of,
    near,
    occlusion_ratio,
    overlaps,
    resolve_scene,
    right_of,
    union_area,
)


def test_box_area_and_center() -> None:
    b = Box(x1=0.2, y1=0.1, x2=0.6, y2=0.5)
    assert pytest.approx(area(b)) == 0.16
    cx, cy = center(b)
    assert pytest.approx(cx) == 0.4
    assert pytest.approx(cy) == 0.3


def test_box_intersection_and_union() -> None:
    b1 = Box(x1=0.0, y1=0.0, x2=0.4, y2=0.4)
    b2 = Box(x1=0.2, y1=0.2, x2=0.6, y2=0.6)
    inter = intersection(b1, b2)
    assert inter is not None
    assert pytest.approx(inter.x1) == 0.2
    assert pytest.approx(inter.y1) == 0.2
    assert pytest.approx(inter.x2) == 0.4
    assert pytest.approx(inter.y2) == 0.4

    assert pytest.approx(intersection_area(b1, b2)) == 0.04
    # Area b1 = 0.16, Area b2 = 0.16, Union = 0.16 + 0.16 - 0.04 = 0.28
    assert pytest.approx(union_area(b1, b2)) == 0.28
    assert pytest.approx(iou(b1, b2)) == 0.04 / 0.28

    # Disjoint boxes
    b3 = Box(x1=0.7, y1=0.7, x2=0.9, y2=0.9)
    assert intersection(b1, b3) is None
    assert intersection_area(b1, b3) == 0.0
    assert iou(b1, b3) == 0.0


def test_crop_box_padding_and_clamping() -> None:
    b = Box(x1=0.05, y1=0.05, x2=0.15, y2=0.15)
    # w=0.1, h=0.1, pad=15% -> pad=0.015
    cropped = crop_box(b, pad=0.15)
    assert pytest.approx(cropped.x1) == 0.035
    assert pytest.approx(cropped.y1) == 0.035
    assert pytest.approx(cropped.x2) == 0.165
    assert pytest.approx(cropped.y2) == 0.165

    # Clamping test
    b_edge = Box(x1=0.01, y1=0.0, x2=0.99, y2=1.0)
    clamped = crop_box(b_edge, pad=0.15)
    assert clamped.x1 == 0.0
    assert clamped.y1 == 0.0
    assert clamped.x2 == 1.0
    assert clamped.y2 == 1.0


def test_spatial_relations() -> None:
    # b1 inside b2: b1 is 0.2x0.2 inside b2 (0.0 to 0.5) -> 100% inside
    b1 = Box(x1=0.1, y1=0.1, x2=0.3, y2=0.3)
    b2 = Box(x1=0.0, y1=0.0, x2=0.5, y2=0.5)
    assert inside(b1, b2)
    assert not inside(b2, b1)  # b2 is not inside b1

    # Overlaps
    assert overlaps(b1, b2)

    # Directional relations
    left_box = Box(x1=0.1, y1=0.4, x2=0.2, y2=0.6)  # cx=0.15, cy=0.5
    right_box = Box(x1=0.5, y1=0.4, x2=0.6, y2=0.6)  # cx=0.55, cy=0.5
    assert left_of(left_box, right_box)
    assert not right_of(left_box, right_box)
    assert right_of(right_box, left_box)

    top_box = Box(x1=0.4, y1=0.1, x2=0.6, y2=0.2)  # cx=0.5, cy=0.15
    bottom_box = Box(x1=0.4, y1=0.7, x2=0.6, y2=0.8)  # cx=0.5, cy=0.75
    assert above(top_box, bottom_box)
    assert not below(top_box, bottom_box)
    assert below(bottom_box, top_box)

    # Near: gap <= 0.5 * max(dim) of b
    target = Box(x1=0.4, y1=0.4, x2=0.6, y2=0.6)  # dim = 0.2 -> 0.5 * dim = 0.1
    near_box = Box(x1=0.65, y1=0.4, x2=0.75, y2=0.6)  # gap = 0.05 <= 0.1
    far_box = Box(x1=0.85, y1=0.4, x2=0.95, y2=0.6)  # gap = 0.25 > 0.1
    assert near(near_box, target)
    assert not near(far_box, target)

    # check_relation dispatch
    assert check_relation("inside", b1, b2)
    assert check_relation("left_of", left_box, right_box)
    with pytest.raises(ValueError, match="Unknown relation"):
        check_relation("diagonal_from", b1, b2)


def test_occlusion_calculation() -> None:
    obj = Box(x1=0.2, y1=0.2, x2=0.4, y2=0.4)  # area = 0.04
    # Hand covers half of object: (0.2, 0.2) to (0.3, 0.4) -> area 0.02 -> 50%
    hand = Box(x1=0.2, y1=0.2, x2=0.3, y2=0.4)
    assert pytest.approx(occlusion_ratio(hand, obj)) == 0.5


def test_slot_resolution_and_occlusion() -> None:
    # 3 tubes in a row along x: [tube0, tube1, tube2]
    tubes = [
        ObjectDef(
            id="tube_a",
            label="Tube A",
            concept="test tube",
            slot=Slot(axis="x", index=0, of=3),
        ),
        ObjectDef(
            id="tube_b",
            label="Tube B",
            concept="test tube",
            slot=Slot(axis="x", index=1, of=3),
        ),
        ObjectDef(
            id="tube_c",
            label="Tube C",
            concept="test tube",
            slot=Slot(axis="x", index=2, of=3),
        ),
    ]

    detections = [
        Detection(
            concept="test tube",
            instance_id=1,
            box=Box(x1=0.6, y1=0.4, x2=0.7, y2=0.8),
            score=0.9,
        ),  # index 2
        Detection(
            concept="test tube",
            instance_id=2,
            box=Box(x1=0.1, y1=0.4, x2=0.2, y2=0.8),
            score=0.95,
        ),  # index 0
        Detection(
            concept="test tube",
            instance_id=3,
            box=Box(x1=0.35, y1=0.4, x2=0.45, y2=0.8),
            score=0.92,
        ),  # index 1
        Detection(
            concept="hand",
            instance_id=4,
            box=Box(x1=0.36, y1=0.4, x2=0.44, y2=0.8),
            score=0.85,
        ),  # occludes tube_b
    ]

    scene = resolve_scene(
        tubes,
        detections,
        det_score_min=0.5,
        occlusion_overlap=0.25,
    )

    resolved_a = scene.get("tube_a")
    assert resolved_a is not None
    assert resolved_a.box == Box(x1=0.1, y1=0.4, x2=0.2, y2=0.8)
    assert not resolved_a.is_occluded
    assert resolved_a.is_valid

    resolved_b = scene.get("tube_b")
    assert resolved_b is not None
    assert resolved_b.box == Box(x1=0.35, y1=0.4, x2=0.45, y2=0.8)
    assert resolved_b.is_occluded
    assert not resolved_b.is_valid

    resolved_c = scene.get("tube_c")
    assert resolved_c is not None
    assert resolved_c.box == Box(x1=0.6, y1=0.4, x2=0.7, y2=0.8)
    assert not resolved_c.is_occluded
    assert resolved_c.is_valid


def test_slot_count_mismatch() -> None:
    tubes = [
        ObjectDef(
            id="tube_a",
            label="Tube A",
            concept="test tube",
            slot=Slot(axis="x", index=0, of=3),
        ),
    ]
    # Only 2 detections present instead of expected 3
    detections = [
        Detection(concept="test tube", instance_id=1, box=Box(x1=0.1, y1=0.4, x2=0.2, y2=0.8)),
        Detection(concept="test tube", instance_id=2, box=Box(x1=0.3, y1=0.4, x2=0.4, y2=0.8)),
    ]
    scene = resolve_scene(tubes, detections)
    resolved = scene.get("tube_a")
    assert resolved is not None
    assert resolved.error == "SLOT_COUNT_MISMATCH"
    assert resolved.box is None
    assert not resolved.is_valid
