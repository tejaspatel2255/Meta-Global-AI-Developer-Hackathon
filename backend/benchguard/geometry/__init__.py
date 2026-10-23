"""Pure geometry package — box math, spatial relations, and slot resolution."""

from benchguard.geometry.boxes import (
    area,
    center,
    crop_box,
    intersection,
    intersection_area,
    iou,
    occlusion_ratio,
    union_area,
)
from benchguard.geometry.relations import (
    above,
    below,
    check_relation,
    inside,
    left_of,
    near,
    overlaps,
    right_of,
)
from benchguard.geometry.resolution import (
    ResolvedObject,
    ResolvedScene,
    resolve_scene,
)

__all__ = [
    "ResolvedObject",
    "ResolvedScene",
    "above",
    "area",
    "below",
    "center",
    "check_relation",
    "crop_box",
    "inside",
    "intersection",
    "intersection_area",
    "iou",
    "left_of",
    "near",
    "occlusion_ratio",
    "overlaps",
    "resolve_scene",
    "right_of",
    "union_area",
]
