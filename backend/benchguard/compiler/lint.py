"""Pure IR lint — docs/CONTRACTS.md §2.4. No I/O, no network."""

from __future__ import annotations

import re
from collections import defaultdict

from benchguard.contracts.enums import Role
from benchguard.contracts.ir import (
    Absent,
    Attribute,
    ObjectDef,
    OrderAlong,
    Predicate,
    Present,
    Procedure,
    Relation,
    Step,
)

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
_STEP_ID = re.compile(r"^s[1-9]\d*$")
_CONCEPT = re.compile(r"^[a-z0-9][a-z0-9 \-]{0,38}$")
_BANNED_WORDS = frozenset({"and", "or", "not"})
_BANNED_CHARS = frozenset(",;+/")


class LintError(Exception):
    def __init__(self, details: list[str]) -> None:
        self.code = "LINT"
        self.details = details
        super().__init__("; ".join(details))


def lint_procedure(proc: Procedure) -> None:
    details: list[str] = []
    object_ids = [obj.id for obj in proc.objects]
    _lint_ids(proc, object_ids, details)
    _lint_objects(proc.objects, details)
    object_set = set(object_ids)
    _lint_steps(proc.steps, object_set, details)
    if details:
        raise LintError(details)


def _lint_ids(proc: Procedure, object_ids: list[str], details: list[str]) -> None:
    if proc.id and not _SNAKE.match(proc.id):
        details.append(f"procedure id {proc.id!r} is not snake_case")
    seen_obj: set[str] = set()
    for oid in object_ids:
        if oid in seen_obj:
            details.append(f"duplicate object id {oid!r}")
        seen_obj.add(oid)
        if not _SNAKE.match(oid):
            details.append(f"object id {oid!r} is not snake_case")
    seen_step: set[str] = set()
    for step in proc.steps:
        if step.id in seen_step:
            details.append(f"duplicate step id {step.id!r}")
        seen_step.add(step.id)
        if not _STEP_ID.match(step.id):
            details.append(f"step id {step.id!r} is not sN")


def _lint_objects(objects: list[ObjectDef], details: list[str]) -> None:
    of_by_concept: dict[str, set[int]] = defaultdict(set)
    for obj in objects:
        _lint_concept(obj.concept, obj.id, details)
        if obj.slot is not None:
            if obj.slot.index >= obj.slot.of:
                details.append(
                    f"{obj.id}: slot.index {obj.slot.index} must be < slot.of {obj.slot.of}"
                )
            of_by_concept[obj.concept].add(obj.slot.of)
    for concept, ofs in of_by_concept.items():
        if len(ofs) > 1:
            details.append(f"concept {concept!r} has inconsistent slot.of {sorted(ofs)}")


def _lint_concept(concept: str, object_id: str, details: list[str]) -> None:
    if not _CONCEPT.match(concept):
        details.append(f"{object_id}: illegal concept {concept!r}")
        return
    if any(ch in concept for ch in _BANNED_CHARS):
        details.append(f"{object_id}: concept {concept!r} contains banned punctuation")
    words = concept.split()
    if len(words) > 4:
        details.append(f"{object_id}: concept {concept!r} has more than 4 words")
    if any(w in _BANNED_WORDS for w in words):
        details.append(f"{object_id}: concept {concept!r} contains and/or/not")


def _lint_steps(
    steps: list[Step],
    object_set: set[str],
    details: list[str],
) -> None:
    by_id = {s.id: s for s in steps}
    for step in steps:
        goals = [p for p in step.expects if p.role == Role.GOAL]
        if not goals:
            details.append(f"{step.id}: needs ≥ 1 goal predicate")
        for pred in step.expects:
            _lint_pred(pred, step.id, object_set, details)
        for sig in step.errors:
            if not sig.when:
                details.append(f"{step.id}: error signature has empty when")
            for pred in sig.when:
                _lint_pred(pred, f"{step.id}.error", object_set, details)
        for dep in step.depends_on:
            if dep not in by_id:
                details.append(f"{step.id}: depends_on unknown step {dep!r}")
            elif by_id[dep].index >= step.index:
                details.append(f"{step.id}: depends_on {dep!r} is not an earlier step")
    _lint_depends_acyclic(steps, details)


def _lint_pred(
    pred: Predicate,
    where: str,
    object_set: set[str],
    details: list[str],
) -> None:
    for oid in _object_ids(pred):
        if oid not in object_set:
            details.append(f"{where}: unknown object {oid!r}")
    if isinstance(pred, OrderAlong) and len(pred.object_ids) < 2:
        details.append(f"{where}: order_along needs ≥ 2 object ids")
    if isinstance(pred, Attribute):
        if not pred.allowed:
            details.append(f"{where}: attribute.allowed is empty")
        overlap = set(pred.allowed) & set(pred.pending)
        if overlap:
            details.append(f"{where}: pending ∩ allowed = {sorted(overlap)}")


def _object_ids(pred: Predicate) -> list[str]:
    if isinstance(pred, Present | Absent | Attribute):
        return [pred.object_id]
    if isinstance(pred, Relation):
        return [pred.subject_id, pred.target_id]
    if isinstance(pred, OrderAlong):
        return list(pred.object_ids)
    return []


def _lint_depends_acyclic(steps: list[Step], details: list[str]) -> None:
    graph = {s.id: list(s.depends_on) for s in steps}
    visiting: set[str] = set()
    seen: set[str] = set()

    def visit(node: str) -> None:
        if node in seen or node not in graph:
            return
        if node in visiting:
            details.append(f"depends_on cycle at {node}")
            return
        visiting.add(node)
        for nxt in graph[node]:
            visit(nxt)
        visiting.remove(node)
        seen.add(node)

    for sid in graph:
        visit(sid)
