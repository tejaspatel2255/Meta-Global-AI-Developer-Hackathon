"""Pure tri-state predicate evaluation — docs/ARCHITECTURE.md §6.1."""

from __future__ import annotations

from benchguard.contracts.enums import PredicateStatus
from benchguard.contracts.ir import (
    Absent,
    Attribute,
    Confirm,
    OrderAlong,
    Predicate,
    Present,
    Relation,
)
from benchguard.contracts.observation import AttributeReading, Observation
from benchguard.contracts.state import PredicateResult
from benchguard.engine.config import EngineConfig
from benchguard.geometry.boxes import center
from benchguard.geometry.relations import check_relation
from benchguard.geometry.resolution import ResolvedScene


def make_query_id(step_id: str, index: int, object_id: str, attribute: str) -> str:
    """Generate canonical query id for attribute queries."""
    return f"{step_id}:{index}:{object_id}:{attribute}"


def evaluate_predicate(
    pred: Predicate,
    step_id: str,
    index: int,
    obs: Observation,
    scene: ResolvedScene,
    cfg: EngineConfig,
    confirmed_prompts: set[str] | None = None,
) -> PredicateResult:
    """Evaluate a single Predicate deterministically into a PredicateResult."""
    if isinstance(pred, Present):
        return _eval_present(pred, step_id, index, scene, cfg)
    if isinstance(pred, Absent):
        return _eval_absent(pred, step_id, index, scene, cfg)
    if isinstance(pred, Relation):
        return _eval_relation(pred, step_id, index, scene, cfg)
    if isinstance(pred, OrderAlong):
        return _eval_order_along(pred, step_id, index, scene, cfg)
    if isinstance(pred, Attribute):
        return _eval_attribute(pred, step_id, index, obs, scene, cfg)
    if isinstance(pred, Confirm):
        return _eval_confirm(pred, step_id, index, confirmed_prompts)

    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.UNKNOWN,
        confidence=0.0,
        reason="UNRECOGNIZED_PREDICATE",
    )


def _eval_present(
    pred: Present,
    step_id: str,
    index: int,
    scene: ResolvedScene,
    cfg: EngineConfig,
) -> PredicateResult:
    resolved = scene.get(pred.object_id)
    if resolved is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OBJECT_NOT_IN_PROCEDURE",
        )

    if resolved.error == "SLOT_COUNT_MISMATCH":
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="SLOT_COUNT_MISMATCH",
        )

    if resolved.is_occluded:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OCCLUDED",
        )

    # For slot-mapped objects, resolved.box indicates presence
    if resolved.object_def.slot is not None:
        if resolved.box is not None:
            conf = resolved.score if resolved.score is not None else 1.0
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.TRUE,
                confidence=conf,
                reason="OK",
            )
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.FALSE,
            confidence=cfg.absence_conf,
            reason="ABSENT",
        )

    # For non-slot objects, count valid detections of the concept
    concept_dets = [d for d in scene.detections if d.concept == resolved.object_def.concept]
    count = len(concept_dets)
    max_count = pred.max_count if pred.max_count is not None else float("inf")

    if pred.min_count <= count <= max_count:
        scores = [d.score for d in concept_dets if d.score is not None]
        conf = min(scores) if scores else 1.0
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.TRUE,
            confidence=conf,
            reason="OK",
        )

    conf = (
        cfg.absence_conf
        if count < pred.min_count
        else (min([d.score for d in concept_dets if d.score is not None]) if concept_dets else 1.0)
    )
    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.FALSE,
        confidence=conf,
        reason="COUNT_OUT_OF_BOUNDS",
    )


def _eval_absent(
    pred: Absent,
    step_id: str,
    index: int,
    scene: ResolvedScene,
    cfg: EngineConfig,
) -> PredicateResult:
    resolved = scene.get(pred.object_id)
    if resolved is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OBJECT_NOT_IN_PROCEDURE",
        )

    if resolved.is_occluded:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OCCLUDED",
        )

    if resolved.error == "SLOT_COUNT_MISMATCH":
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="SLOT_COUNT_MISMATCH",
        )

    if resolved.box is not None:
        conf = resolved.score if resolved.score is not None else 1.0
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.FALSE,
            confidence=conf,
            reason="PRESENT",
        )

    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.TRUE,
        confidence=cfg.absence_conf,
        reason="OK",
    )


def _eval_relation(
    pred: Relation,
    step_id: str,
    index: int,
    scene: ResolvedScene,
    cfg: EngineConfig,
) -> PredicateResult:
    subj = scene.get(pred.subject_id)
    tgt = scene.get(pred.target_id)

    if subj is None or tgt is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OBJECT_NOT_IN_PROCEDURE",
        )

    if subj.error is not None or tgt.error is not None:
        err = subj.error or tgt.error
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason=err or "RESOLUTION_ERROR",
        )

    if subj.is_occluded or tgt.is_occluded:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OCCLUDED",
        )

    if subj.box is None or tgt.box is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="MISSING_OBJECT",
        )

    holds = check_relation(pred.relation, subj.box, tgt.box, rel_margin=cfg.rel_margin)
    if pred.negate:
        holds = not holds

    scores = [s for s in (subj.score, tgt.score) if s is not None]
    conf = min(scores) if scores else 1.0

    if holds:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.TRUE,
            confidence=conf,
            reason="OK",
        )

    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.FALSE,
        confidence=conf,
        reason="RELATION_FAILED",
    )


def _eval_order_along(
    pred: OrderAlong,
    step_id: str,
    index: int,
    scene: ResolvedScene,
    cfg: EngineConfig,
) -> PredicateResult:
    boxes = []
    scores = []
    for oid in pred.object_ids:
        resolved = scene.get(oid)
        if resolved is None:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.UNKNOWN,
                confidence=0.0,
                reason="OBJECT_NOT_IN_PROCEDURE",
            )
        if resolved.error is not None:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.UNKNOWN,
                confidence=0.0,
                reason=resolved.error,
            )
        if resolved.is_occluded:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.UNKNOWN,
                confidence=0.0,
                reason="OCCLUDED",
            )
        if resolved.box is None:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.UNKNOWN,
                confidence=0.0,
                reason="MISSING_OBJECT",
            )
        boxes.append(resolved.box)
        if resolved.score is not None:
            scores.append(resolved.score)

    axis_idx = 0 if pred.axis == "x" else 1
    centers = [center(b)[axis_idx] for b in boxes]

    conf = min(scores) if scores else 1.0
    for i in range(len(centers) - 1):
        if (centers[i + 1] - centers[i]) <= cfg.rel_margin:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.FALSE,
                confidence=conf,
                reason="ORDER_WRONG",
            )

    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.TRUE,
        confidence=conf,
        reason="OK",
    )


def _eval_attribute(
    pred: Attribute,
    step_id: str,
    index: int,
    obs: Observation,
    scene: ResolvedScene,
    cfg: EngineConfig,
) -> PredicateResult:
    resolved = scene.get(pred.object_id)
    if resolved is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OBJECT_NOT_IN_PROCEDURE",
        )

    if resolved.error is not None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason=resolved.error,
        )

    if resolved.is_occluded:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="OCCLUDED",
        )

    if resolved.box is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="MISSING_OBJECT",
        )

    # If gate is defined, gate must evaluate to TRUE
    if pred.gate is not None:
        gate_res = evaluate_predicate(pred.gate, step_id, index, obs, scene, cfg)
        if gate_res.status != PredicateStatus.TRUE:
            return PredicateResult(
                step_id=step_id,
                index=index,
                status=PredicateStatus.UNKNOWN,
                confidence=0.0,
                reason="GATED",
            )

    # Find matching reading in obs
    canonical_qid = make_query_id(step_id, index, pred.object_id, pred.attribute)
    matched_reading: AttributeReading | None = None
    for r in obs.readings:
        if (
            r.query_id == canonical_qid
            or r.query_id == pred.object_id
            or r.query_id.startswith(f"{pred.object_id}:")
        ):
            matched_reading = r
            break

    if matched_reading is None:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=0.0,
            reason="NO_READING",
        )

    reading_val = matched_reading.value.strip().lower()
    reading_conf = matched_reading.confidence

    if reading_val == "unclear" or reading_conf < cfg.vlm_conf_min:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.UNKNOWN,
            confidence=reading_conf,
            reason="UNCLEAR" if reading_val == "unclear" else "LOW_CONF",
        )

    # 1. Allowed reading
    allowed_norm = [a.lower() for a in pred.allowed]
    if reading_val in allowed_norm:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.TRUE,
            confidence=reading_conf,
            reason="OK",
        )

    # 2. Pending reading: benign "not yet done" value
    pending_norm = [p.lower() for p in pred.pending]
    if reading_val in pending_norm:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.FALSE,
            confidence=reading_conf,
            reason="PENDING_VALUE",
            benign=True,
        )

    # 3. Reading not in allowed or pending
    if reading_conf >= cfg.alarm_conf_min:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.FALSE,
            confidence=reading_conf,
            reason="EVIDENCE",
            benign=False,
        )

    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.UNKNOWN,
        confidence=reading_conf,
        reason="LOW_CONF",
    )


def _eval_confirm(
    pred: Confirm,
    step_id: str,
    index: int,
    confirmed_prompts: set[str] | None,
) -> PredicateResult:
    if confirmed_prompts and pred.prompt in confirmed_prompts:
        return PredicateResult(
            step_id=step_id,
            index=index,
            status=PredicateStatus.TRUE,
            confidence=1.0,
            reason="CONFIRMED",
        )
    return PredicateResult(
        step_id=step_id,
        index=index,
        status=PredicateStatus.UNKNOWN,
        confidence=0.0,
        reason="AWAITING_CONFIRMATION",
    )
