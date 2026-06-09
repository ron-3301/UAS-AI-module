# tests for the iou tracker.
from __future__ import annotations

from src.detection.tracker import IouTracker
from src.types import RawDetection


def _det(x: int, y: int, w: int = 50, h: int = 50, cls: str = "A") -> RawDetection:
    return RawDetection(bbox_px=(x, y, w, h), detection_class=cls, detection_confidence=0.9)


def test_tracker_assigns_stable_id_across_frames() -> None:
    t = IouTracker()
    d1 = _det(100, 100)
    out1 = t.update(frame_id=0, detections=[d1])
    assert out1[0].track_id == 0

    d2 = _det(105, 102)  # small drift, high IoU
    out2 = t.update(frame_id=1, detections=[d2])
    assert out2[0].track_id == 0


def test_tracker_new_id_for_unmatched() -> None:
    t = IouTracker()
    t.update(0, [_det(0, 0)])
    out = t.update(1, [_det(500, 500)])
    assert out[0].track_id != 0


def test_tracker_drops_stale() -> None:
    t = IouTracker(max_age=2)
    t.update(0, [_det(100, 100)])
    # Same box re-appearing at frame 10: previous track has aged out.
    out = t.update(10, [_det(100, 100)])
    assert out[0].track_id != 0


def test_tracker_class_separates_tracks() -> None:
    t = IouTracker()
    t.update(0, [_det(100, 100, cls="A")])
    out = t.update(1, [_det(100, 100, cls="B")])     # same box, different class
    assert out[0].track_id != 0
