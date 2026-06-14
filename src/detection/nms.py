# class-agnostic NMS. pure python so it can be unit-tested without numpy.
# default iou=0.45 per doc 02 §2.
from __future__ import annotations

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
