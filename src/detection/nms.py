from __future__ import annotations

# --- OLD CODE FROM SRC ---
# class-agnostic NMS. pure python so it can be unit-tested without numpy.
# default iou=0.45 per doc 02 §2.


from src.types import RawDetection


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh

    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def class_agnostic_nms(
    detections: list[RawDetection], iou_threshold: float = 0.45,
) -> list[RawDetection]:
    # highest-confidence wins, regardless of class label.
    ordered = sorted(detections, key=lambda d: d.detection_confidence, reverse=True)
    kept: list[RawDetection] = []
    while ordered:
        top = ordered.pop(0)
        kept.append(top)
        ordered = [d for d in ordered if _iou(top.bbox_px, d.bbox_px) < iou_threshold]
    return kept

# --- END OLD CODE ---

"""Bounding-box utilities and non-maximum suppression."""


from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BoxCandidate:
    """Intermediate detection candidate used before dataclass conversion."""

    x1: float
    y1: float
    x2: float
    y2: float
    score: float
    class_id: int

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


def box_iou(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute intersection-over-union for two xyxy boxes."""

    ax1, ay1, ax2, ay2 = map(float, a)
    bx1, by1, bx2, by2 = map(float, b)

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


def nms(
    candidates: Sequence[BoxCandidate],
    *,
    iou_threshold: float,
    class_agnostic: bool = False,
    max_detections: int = 300,
) -> tuple[BoxCandidate, ...]:
    """Apply greedy non-maximum suppression.

    Args:
        candidates: candidate boxes in image coordinates.
        iou_threshold: boxes with IoU greater than this threshold are suppressed.
        class_agnostic: when false, only boxes of the same class suppress each other.
        max_detections: cap on returned boxes.
    """

    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be in [0, 1]")
    if max_detections <= 0:
        return ()

    remaining = sorted(candidates, key=lambda item: item.score, reverse=True)
    kept: list[BoxCandidate] = []

    while remaining and len(kept) < max_detections:
        current = remaining.pop(0)
        kept.append(current)
        survivors = []
        for candidate in remaining:
            same_class = candidate.class_id == current.class_id
            if not class_agnostic and not same_class:
                survivors.append(candidate)
                continue
            if box_iou(current.bbox, candidate.bbox) <= iou_threshold:
                survivors.append(candidate)
        remaining = survivors

    return tuple(kept)


def clip_xyxy(
    bbox: Sequence[float], *, width: int, height: int
) -> tuple[float, float, float, float]:
    """Clip xyxy coordinates to image bounds."""

    x1, y1, x2, y2 = map(float, bbox)
    x1 = min(max(x1, 0.0), float(width))
    y1 = min(max(y1, 0.0), float(height))
    x2 = min(max(x2, 0.0), float(width))
    y2 = min(max(y2, 0.0), float(height))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)
