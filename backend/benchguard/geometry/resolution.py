"""Object resolution and occlusion calculation — docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from dataclasses import dataclass

from benchguard.contracts.boxes import Box
from benchguard.contracts.ir import ObjectDef
from benchguard.contracts.observation import Detection
from benchguard.geometry.boxes import center, occlusion_ratio


@dataclass(frozen=True)
class ResolvedObject:
    object_def: ObjectDef
    box: Box | None
    score: float | None = None
    is_occluded: bool = False
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """True if successfully resolved, unoccluded, and without errors."""
        return self.box is not None and not self.is_occluded and self.error is None


@dataclass(frozen=True)
class ResolvedScene:
    by_id: dict[str, ResolvedObject]
    hands: list[Detection]
    detections: list[Detection]

    def get(self, object_id: str) -> ResolvedObject | None:
        return self.by_id.get(object_id)


def resolve_scene(
    objects: list[ObjectDef],
    detections: list[Detection],
    det_score_min: float = 0.5,
    occlusion_overlap: float = 0.25,
) -> ResolvedScene:
    """Resolve procedure ObjectDefs to spatial detections and compute occlusion."""
    # 1. Filter valid detections by minimum score
    valid_dets = [d for d in detections if d.score is None or d.score >= det_score_min]

    # Group detections by concept
    by_concept: dict[str, list[Detection]] = {}
    hands: list[Detection] = []
    for d in valid_dets:
        if d.concept == "hand":
            hands.append(d)
        by_concept.setdefault(d.concept, []).append(d)

    resolved_map: dict[str, ResolvedObject] = {}

    for obj in objects:
        concept_dets = by_concept.get(obj.concept, [])

        if obj.slot is not None:
            # Slot-based resolution (k-th of n along axis)
            slot = obj.slot
            if len(concept_dets) != slot.of:
                resolved_map[obj.id] = ResolvedObject(
                    object_def=obj,
                    box=None,
                    score=None,
                    error="SLOT_COUNT_MISMATCH",
                )
                continue

            # Sort along specified axis: x -> left to right; y -> top to bottom
            if slot.axis == "x":
                sorted_dets = sorted(concept_dets, key=lambda d: center(d.box)[0])
            else:
                sorted_dets = sorted(concept_dets, key=lambda d: center(d.box)[1])

            matched = sorted_dets[slot.index]
            resolved_box = matched.box
            resolved_score = matched.score
        else:
            # Non-slot resolution: match concept; take best-scoring detection if present
            if not concept_dets:
                resolved_map[obj.id] = ResolvedObject(
                    object_def=obj,
                    box=None,
                    score=None,
                    error="NOT_FOUND",
                )
                continue
            best_det = max(concept_dets, key=lambda d: d.score if d.score is not None else 1.0)
            resolved_box = best_det.box
            resolved_score = best_det.score

        # Check occlusion against all hands
        is_occ = False
        if resolved_box is not None:
            for hand in hands:
                if occlusion_ratio(hand.box, resolved_box) >= occlusion_overlap:
                    is_occ = True
                    break

        resolved_map[obj.id] = ResolvedObject(
            object_def=obj,
            box=resolved_box,
            score=resolved_score,
            is_occluded=is_occ,
            error=None,
        )

    return ResolvedScene(
        by_id=resolved_map,
        hands=hands,
        detections=valid_dets,
    )
