"""Core runtime data models.

The project deliberately uses lightweight dataclasses for the runtime core so the
Jetson deployment path remains easy to audit and free of training-framework
coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


CLASS_LABELS = {
    "Person",
    "Vehicle-Wheeled",
    "Vehicle-Tracked",
    "Aircraft-Rotary",
    "Aircraft-Fixed",
    "Watercraft",
    "Structure-Temp",
    "Unknown",
}


@dataclass(frozen=True)
class Frame:
    """A captured video frame.

    `data` may be a NumPy array, bytes, or any camera-backend object. The core
    tests use bytes to avoid requiring OpenCV or camera hardware.
    """

    frame_id: str
    timestamp_utc: datetime
    width: int
    height: int
    data: Any = None


@dataclass(frozen=True)
class Telemetry:
    """Ownship state required for advisory output and geolocation."""

    timestamp_utc: datetime
    lat_deg: float
    lon_deg: float
    alt_msl_m: float
    alt_agl_m: float | None = None
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    velocity_ned_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class CameraIntrinsics:
    """Minimal calibrated pinhole camera model."""

    camera_id: str
    width: int
    height: int
    fx: float
    fy: float
    cx: float
    cy: float
    mount_roll_deg: float = 0.0
    mount_pitch_deg: float = -90.0
    mount_yaw_deg: float = 0.0

    def validate(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("camera resolution must be positive")
        if self.fx <= 0 or self.fy <= 0:
            raise ValueError("camera focal lengths must be positive")


@dataclass(frozen=True)
class Detection:
    """Detector output before safety filtering."""

    class_label: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    track_id: str | int | None = None
    sublabel: str | None = None
    id_confidence: float | None = None
    is_civilian: bool | None = None
    source: str = "local"

    def validate(self) -> None:
        if self.class_label not in CLASS_LABELS:
            raise ValueError(f"unknown class label: {self.class_label}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("detection confidence must be in [0, 1]")
        if len(self.bbox_xyxy) != 4:
            raise ValueError("bbox_xyxy must contain four coordinates")
        x1, y1, x2, y2 = self.bbox_xyxy
        if x2 < x1 or y2 < y1:
            raise ValueError("bbox_xyxy must satisfy x2>=x1 and y2>=y1")


@dataclass(frozen=True)
class GeoPoint:
    """Estimated object location and uncertainty."""

    lat_deg: float | None
    lon_deg: float | None
    alt_msl_m: float | None = None
    cep_m: float | None = None
    covariance: tuple[float, ...] | None = None
    valid: bool = True
    reason: str | None = None


@dataclass(frozen=True)
class Prediction:
    """Optional intent/TCPA estimate."""

    intent: str | None = None
    intent_confidence: float | None = None
    tcpa_s: float | None = None
    closest_approach_m: float | None = None


@dataclass(frozen=True)
class EnrichedDetection:
    """Detection plus geolocation/prediction context."""

    detection: Detection
    geolocation: GeoPoint | None = None
    prediction: Prediction | None = None
    risk_score: float | None = None
    source_uas_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HealthStatus:
    """Runtime health summary for advisory packets."""

    status: str = "ok"  # ok | degraded | invalid
    warnings: tuple[str, ...] = field(default_factory=tuple)
    latency_ms: float | None = None
    camera_stale_ms: int | None = None
    telemetry_stale_ms: int | None = None
    temperature_c: float | None = None
    power_w: float | None = None


@dataclass(frozen=True)
class PipelineResult:
    """Output returned by one pipeline iteration."""

    frame: Frame
    telemetry: Telemetry
    detections: tuple[EnrichedDetection, ...]
    health: HealthStatus
    advisory: dict[str, Any]


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp helper."""

    return datetime.now(timezone.utc)
