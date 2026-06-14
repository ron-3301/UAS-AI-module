from __future__ import annotations

import numpy as np

from uas_ai_module.geolocation.transforms import apply_rotation, pinhole_camera_ray, rotation_matrix_zyx
from uas_ai_module.models import Detection
from uas_ai_module.tracking.track_manager import TrackManager


def test_track_manager_assigns_stable_ids_across_overlapping_frames() -> None:
    tracker = TrackManager(iou_threshold=0.2)
    first = tracker.update((Detection("Vehicle-Wheeled", 0.9, (10, 10, 50, 50)),))
    second = tracker.update((Detection("Vehicle-Wheeled", 0.9, (12, 12, 52, 52)),))
    assert first[0].track_id == second[0].track_id
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].age_frames == 2


def test_track_manager_expires_missed_tracks() -> None:
    tracker = TrackManager(max_missed_frames=1)
    first = tracker.update((Detection("Vehicle-Wheeled", 0.9, (10, 10, 50, 50)),))
    assert first[0].track_id is not None
    tracker.update(())
    assert len(tracker.tracks) == 1
    tracker.update(())
    assert tracker.tracks == ()


def test_rotation_helpers_identity_and_ray_normalization() -> None:
    rotation = rotation_matrix_zyx(0, 0, 0)
    assert np.allclose(rotation, np.eye(3))
    ray = pinhole_camera_ray(0.0, 0.0)
    assert np.allclose(ray, np.array([0.0, 0.0, 1.0]))
    assert np.isclose(np.linalg.norm(ray), 1.0)
    assert np.allclose(apply_rotation(rotation, ray), ray)
