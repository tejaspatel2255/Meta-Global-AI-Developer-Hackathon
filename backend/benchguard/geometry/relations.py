"""Pure geometric relations between normalized Box objects — docs/ARCHITECTURE.md §6.2."""

from __future__ import annotations

import math
from typing import Literal

from benchguard.contracts.boxes import Box
from benchguard.geometry.boxes import area, center, intersection_area, iou

RelationType = Literal["left_of", "right_of", "above", "below", "inside", "overlaps", "near"]


def inside(a: Box, b: Box, min_containment: float = 0.8) -> bool:
    """Return True if area(a∩b) / area(a) >= min_containment (default 0.8)."""
    area_a = area(a)
    if area_a <= 0.0:
        return False
    return (intersection_area(a, b) / area_a) >= min_containment


def overlaps(a: Box, b: Box) -> bool:
    """Return True if IoU > 0."""
    return iou(a, b) > 0.0


def left_of(a: Box, b: Box, rel_margin: float = 0.01) -> bool:
    """Return True if a is left of b by centre delta > rel_margin."""
    ca = center(a)
    cb = center(b)
    return (cb[0] - ca[0]) > rel_margin


def right_of(a: Box, b: Box, rel_margin: float = 0.01) -> bool:
    """Return True if a is right of b by centre delta > rel_margin."""
    ca = center(a)
    cb = center(b)
    return (ca[0] - cb[0]) > rel_margin


def above(a: Box, b: Box, rel_margin: float = 0.01) -> bool:
    """Return True if a is above b by centre delta > rel_margin (top-left origin)."""
    ca = center(a)
    cb = center(b)
    return (cb[1] - ca[1]) > rel_margin


def below(a: Box, b: Box, rel_margin: float = 0.01) -> bool:
    """Return True if a is below b by centre delta > rel_margin (top-left origin)."""
    ca = center(a)
    cb = center(b)
    return (ca[1] - cb[1]) > rel_margin


def box_gap(a: Box, b: Box) -> float:
    """Compute the shortest Euclidean gap between boundaries of box a and box b."""
    gap_x = max(0.0, max(a.x1, b.x1) - min(a.x2, b.x2))
    gap_y = max(0.0, max(a.y1, b.y1) - min(a.y2, b.y2))
    if gap_x == 0.0 and gap_y == 0.0:
        return 0.0
    return math.hypot(gap_x, gap_y)


def near(a: Box, b: Box) -> bool:
    """Return True if gap <= 0.5 * max(box dim) of b."""
    gap = box_gap(a, b)
    max_dim_b = max(b.x2 - b.x1, b.y2 - b.y1)
    return gap <= (0.5 * max_dim_b)


def check_relation(
    rel: str,
    subject: Box,
    target: Box,
    rel_margin: float = 0.01,
) -> bool:
    """Dispatch relation check by name."""
    if rel == "inside":
        return inside(subject, target)
    if rel == "overlaps":
        return overlaps(subject, target)
    if rel == "left_of":
        return left_of(subject, target, rel_margin=rel_margin)
    if rel == "right_of":
        return right_of(subject, target, rel_margin=rel_margin)
    if rel == "above":
        return above(subject, target, rel_margin=rel_margin)
    if rel == "below":
        return below(subject, target, rel_margin=rel_margin)
    if rel == "near":
        return near(subject, target)
    msg = f"Unknown relation {rel!r}"
    raise ValueError(msg)
