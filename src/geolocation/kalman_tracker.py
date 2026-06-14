# layer 4 stub. per-track Kalman filter (position+velocity in local ENU).
# lands Phase 4 W12.
from __future__ import annotations


class GeoKalmanTracker:
    def __init__(self) -> None:
        self._filters: dict[int, object] = {}

    def update(self, track_id: int, observation):  # pragma: no cover - stub
        raise NotImplementedError("Kalman tracker lands Phase 4 W12")
