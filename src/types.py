# shared dataclasses used between the pipeline layers.
# kept here so detection / id / geo / output don't import each other and
# end up in circular-import hell.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FramePacket:
    # one of these per frame, produced by layer 1
    frame_id: int
    timestamp_utc: str
    image: Any                          # np.ndarray, BGR
    telemetry: dict[str, Any]           # lat/lon/alt_msl/alt_agl/roll/pitch/yaw at minimum
    telemetry_stale: bool = False
    capture_latency_ms: float = 0.0     # for profiling


@dataclass
class RawDetection:
    bbox_px: tuple[int, int, int, int]   # x, y, w, h
    detection_class: str
    detection_confidence: float
    track_id: int | None = None


@dataclass
class IdentifiedDetection:
    raw: RawDetection
    id_label: str | None = None
    id_confidence: float | None = None
    threat_score: float = 0.0


@dataclass
class GeolocatedDetection:
    identified: IdentifiedDetection
    geolocation: dict[str, float] | None = None     # {'lat','lon','cep_m'}


@dataclass
class StageTiming:
    """per-stage latency record. keyed by stage name."""
    stages: dict[str, float] = field(default_factory=dict)

    def add(self, name: str, t: float) -> None:
        self.stages[name] = t

    def total_ms(self) -> float:
        return sum(self.stages.values())
