# tests for class-agnostic nms.
from __future__ import annotations

from src.detection.nms import _iou, class_agnostic_nms
from src.types import RawDetection


def _det(x: int, y: int, w: int, h: int, conf: float, cls: str = "A") -> RawDetection:
    return RawDetection(bbox_px=(x, y, w, h), detection_class=cls, detection_confidence=conf)


def test_iou_simple_overlap() -> None:
    a = (0, 0, 100, 100)
    b = (50, 50, 100, 100)
    # intersection 50x50, union = 100*100 + 100*100 - 2500 = 17500
    assert abs(_iou(a, b) - (2500 / 17500)) < 1e-9


def test_iou_no_overlap() -> None:
    assert _iou((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0


def test_nms_suppresses_lower_confidence() -> None:
    kept = class_agnostic_nms([
        _det(10, 10, 100, 100, 0.9),
        _det(15, 15, 100, 100, 0.7),   # heavy overlap -> suppressed
        _det(200, 200, 50, 50, 0.6),    # disjoint -> kept
    ], iou_threshold=0.45)
    assert len(kept) == 2
    assert kept[0].detection_confidence == 0.9
    assert kept[1].detection_confidence == 0.6


def test_nms_class_agnostic() -> None:
    # Two heavily-overlapping boxes of *different* classes: still suppressed.
    kept = class_agnostic_nms([
        _det(0, 0, 100, 100, 0.9, cls="A"),
        _det(0, 0, 100, 100, 0.8, cls="B"),
    ], iou_threshold=0.45)
    assert len(kept) == 1
    assert kept[0].detection_class == "A"


def test_nms_empty() -> None:
    assert class_agnostic_nms([]) == []
