from __future__ import annotations

"""Runtime health and fail-closed staleness checks."""


from dataclasses import dataclass
from datetime import datetime, timezone

from models import Frame, HealthStatus, Telemetry


@dataclass(frozen=True)
class HealthThresholds:
    max_frame_stale_ms: int = 1000
    max_telemetry_stale_ms: int = 1000


def staleness_ms(timestamp: datetime, *, now: datetime | None = None) -> int:
    """Return non-negative age of a timestamp in milliseconds."""

    now = now or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    now = now.astimezone(timezone.utc)
    return max(0, int((now - timestamp).total_seconds() * 1000.0))


def evaluate_runtime_health(
    frame: Frame,
    telemetry: Telemetry,
    *,
    thresholds: HealthThresholds = HealthThresholds(),
    base_warnings: tuple[str, ...] = (),
    latency_ms: float | None = None,
    now: datetime | None = None,
) -> HealthStatus:
    """Evaluate packet-level health and sensor staleness.

    Stale frame/telemetry conditions are marked degraded here and later cause
    emitted detections to be invalidated by the serializer. This creates an
    explicit fail-closed path instead of silently emitting stale advisories.
    """

    now = now or datetime.now(timezone.utc)
    frame_stale = staleness_ms(frame.timestamp_utc, now=now)
    telemetry_stale = staleness_ms(telemetry.timestamp_utc, now=now)

    warnings = list(base_warnings)
    if frame_stale > thresholds.max_frame_stale_ms:
        warnings.append(f"stale_frame: {frame_stale} ms")
    if telemetry_stale > thresholds.max_telemetry_stale_ms:
        warnings.append(f"stale_telemetry: {telemetry_stale} ms")

    status = "degraded" if warnings else "ok"
    return HealthStatus(
        status=status,
        warnings=tuple(warnings),
        latency_ms=latency_ms,
        camera_stale_ms=frame_stale,
        telemetry_stale_ms=telemetry_stale,
    )
