"""Pure box math operations on normalized Box contracts."""

from __future__ import annotations

from benchguard.contracts.boxes import Box


def area(box: Box) -> float:
    """Return width * height of the normalized box."""
    w = max(0.0, box.x2 - box.x1)
    h = max(0.0, box.y2 - box.y1)
    return w * h


def center(box: Box) -> tuple[float, float]:
    """Return (cx, cy) center coordinates."""
    return ((box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0)


def intersection(a: Box, b: Box) -> Box | None:
    """Return intersection box of a and b, or None if no overlap."""
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return Box(x1=x1, y1=y1, x2=x2, y2=y2)


def intersection_area(a: Box, b: Box) -> float:
    """Return area of intersection between a and b."""
    inter = intersection(a, b)
    if inter is None:
        return 0.0
    return area(inter)


def union_area(a: Box, b: Box) -> float:
    """Return union area of a and b."""
    area_a = area(a)
    area_b = area(b)
    inter = intersection_area(a, b)
    return max(0.0, area_a + area_b - inter)


def iou(a: Box, b: Box) -> float:
    """Compute Intersection-over-Union."""
    u = union_area(a, b)
    if u <= 0.0:
        return 0.0
    return intersection_area(a, b) / u


def crop_box(box: Box, pad: float = 0.15) -> Box:
    """Pads box by `pad` fraction of dimensions and clamps to [0.0, 1.0]."""
    w = box.x2 - box.x1
    h = box.y2 - box.y1
    pad_w = w * pad
    pad_h = h * pad
    return Box(
        x1=max(0.0, box.x1 - pad_w),
        y1=max(0.0, box.y1 - pad_h),
        x2=min(1.0, box.x2 + pad_w),
        y2=min(1.0, box.y2 + pad_h),
    )


def occlusion_ratio(hand_box: Box, object_box: Box) -> float:
    """Compute intersection(hand_box, object_box) / area(object_box)."""
    obj_area = area(object_box)
    if obj_area <= 0.0:
        return 0.0
    return intersection_area(hand_box, object_box) / obj_area
