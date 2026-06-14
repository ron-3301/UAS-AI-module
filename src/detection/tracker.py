from __future__ import annotations

# greedy IoU tracker. placeholder for ByteTrack (Phase 3 W7).
# assigns stable, monotonic track_id when IoU vs a prior box > threshold,
# ages out tracks not seen for max_age frames.


from dataclasses import dataclass

from src.detection.nms import _iou
from src.types import RawDetection


@dataclass
class _Track:
    track_id: int
    bbox_px: tuple[int, int, int, int]
    detection_class: str
    last_seen_frame: int


class IouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 10) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._tracks: list[_Track] = []
        self._next_id = 0

    def update(self, frame_id: int, detections: list[RawDetection]) -> list[RawDetection]:
        # age out stale tracks
        self._tracks = [t for t in self._tracks if (frame_id - t.last_seen_frame) <= self.max_age]

        out: list[RawDetection] = []
        for det in detections:
            best_iou = 0.0
            best: _Track | None = None
            for t in self._tracks:
                if t.detection_class != det.detection_class:
                    continue
                v = _iou(t.bbox_px, det.bbox_px)
                if v > best_iou:
                    best_iou = v
                    best = t

            if best is not None and best_iou >= self.iou_threshold:
                best.bbox_px = det.bbox_px
                best.last_seen_frame = frame_id
                det.track_id = best.track_id
            else:
                # new track
                tid = self._next_id
                self._next_id += 1
                self._tracks.append(_Track(
                    track_id=tid,
                    bbox_px=det.bbox_px,
                    detection_class=det.detection_class,
                    last_seen_frame=frame_id,
                ))
                det.track_id = tid
            out.append(det)
        return out
