"""Lightweight local detection-to-track assignment.

This is not a replacement for a full Kalman/IMM tracker. It is a deterministic
baseline that provides stable local track IDs across replay/test frames and gives
Phase 13 something concrete to audit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math

from uas_ai_module.detection.nms import box_iou
from uas_ai_module.models import Detection


@dataclass(frozen=True)
class TrackState:
    track_id: str
    class_label: str
    bbox_xyxy: tuple[float, float, float, float]
    age_frames: int
    missed_frames: int
    last_seen_frame: int


class TrackManager:
    """Greedy IoU/centroid tracker for stable local IDs."""

    def __init__(
        self,
        *,
        iou_threshold: float = 0.30,
        max_center_distance_px: float = 80.0,
        max_missed_frames: int = 5,
        track_prefix: str = "trk",
    ) -> None:
        if not 0 <= iou_threshold <= 1:
            raise ValueError("iou_threshold must be in [0, 1]")
        if max_center_distance_px < 0:
            raise ValueError("max_center_distance_px must be non-negative")
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames must be non-negative")
        self.iou_threshold = iou_threshold
        self.max_center_distance_px = max_center_distance_px
        self.max_missed_frames = max_missed_frames
        self.track_prefix = track_prefix
        self._tracks: dict[str, TrackState] = {}
        self._frame_index = 0
        self._next_id = 1

    @property
    def tracks(self) -> tuple[TrackState, ...]:
        return tuple(sorted(self._tracks.values(), key=lambda item: item.track_id))

    def update(self, detections: tuple[Detection, ...]) -> tuple[Detection, ...]:
        """Assign track IDs to detections and update track lifecycle state."""

        self._frame_index += 1
        assigned_tracks: set[str] = set()
        output: list[Detection] = []

        for detection in detections:
            detection.validate()
            if detection.track_id is not None:
                track_id = str(detection.track_id)
            else:
                track_id = self._best_match(detection, assigned_tracks) or self._new_track_id()
            assigned_tracks.add(track_id)
            previous = self._tracks.get(track_id)
            self._tracks[track_id] = TrackState(
                track_id=track_id,
                class_label=detection.class_label,
                bbox_xyxy=detection.bbox_xyxy,
                age_frames=(previous.age_frames + 1 if previous else 1),
                missed_frames=0,
                last_seen_frame=self._frame_index,
            )
            output.append(replace(detection, track_id=track_id))

        self._age_unassigned_tracks(assigned_tracks)
        return tuple(output)

    def _best_match(self, detection: Detection, assigned_tracks: set[str]) -> str | None:
        best_id: str | None = None
        best_score = -1.0
        for track_id, track in self._tracks.items():
            if track_id in assigned_tracks or track.class_label != detection.class_label:
                continue
            iou = box_iou(track.bbox_xyxy, detection.bbox_xyxy)
            center_dist = _center_distance(track.bbox_xyxy, detection.bbox_xyxy)
            if iou >= self.iou_threshold:
                score = 10.0 + iou
            elif center_dist <= self.max_center_distance_px:
                score = 1.0 - (center_dist / max(self.max_center_distance_px, 1e-6))
            else:
                continue
            if score > best_score:
                best_score = score
                best_id = track_id
        return best_id

    def _new_track_id(self) -> str:
        track_id = f"{self.track_prefix}-{self._next_id:06d}"
        self._next_id += 1
        return track_id

    def _age_unassigned_tracks(self, assigned_tracks: set[str]) -> None:
        for track_id, track in list(self._tracks.items()):
            if track_id in assigned_tracks:
                continue
            missed = self._frame_index - track.last_seen_frame
            if missed > self.max_missed_frames:
                del self._tracks[track_id]
            else:
                self._tracks[track_id] = replace(track, missed_frames=missed)


def _center_distance(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    acx = (ax1 + ax2) / 2.0
    acy = (ay1 + ay2) / 2.0
    bcx = (bx1 + bx2) / 2.0
    bcy = (by1 + by2) / 2.0
    return math.hypot(acx - bcx, acy - bcy)
