"""Runtime metric extraction from advisory packets."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeMetricSnapshot:
    health_status: str
    latency_ms: float | None
    detection_count: int
    invalid_detection_count: int
    warning_count: int
    stale_camera_ms: int | None
    stale_telemetry_ms: int | None


class RuntimeMetricsCollector:
    """Collect simple runtime metrics from advisory packets."""

    def from_packet(self, packet: dict[str, Any]) -> RuntimeMetricSnapshot:
        detections = packet.get("detections", []) or []
        health = packet.get("health", {}) or {}
        invalid = sum(1 for item in detections if item.get("validity_flag") is False)
        warnings = health.get("warnings", []) or []
        return RuntimeMetricSnapshot(
            health_status=str(health.get("status", "unknown")),
            latency_ms=health.get("latency_ms"),
            detection_count=len(detections),
            invalid_detection_count=invalid,
            warning_count=len(warnings),
            stale_camera_ms=health.get("camera_stale_ms"),
            stale_telemetry_ms=health.get("telemetry_stale_ms"),
        )


def prometheus_text(snapshot: RuntimeMetricSnapshot, *, prefix: str = "uas_ai") -> str:
    """Render metrics in Prometheus text exposition format without dependencies."""

    status_value = {"ok": 0, "degraded": 1, "invalid": 2}.get(snapshot.health_status, 3)
    lines = [
        f"# TYPE {prefix}_health_status gauge",
        f"{prefix}_health_status {status_value}",
        f"# TYPE {prefix}_detections_total gauge",
        f"{prefix}_detections_total {snapshot.detection_count}",
        f"# TYPE {prefix}_invalid_detections_total gauge",
        f"{prefix}_invalid_detections_total {snapshot.invalid_detection_count}",
        f"# TYPE {prefix}_warnings_total gauge",
        f"{prefix}_warnings_total {snapshot.warning_count}",
    ]
    if snapshot.latency_ms is not None:
        lines.extend([f"# TYPE {prefix}_latency_ms gauge", f"{prefix}_latency_ms {float(snapshot.latency_ms)}"])
    if snapshot.stale_camera_ms is not None:
        lines.extend([f"# TYPE {prefix}_camera_stale_ms gauge", f"{prefix}_camera_stale_ms {int(snapshot.stale_camera_ms)}"])
    if snapshot.stale_telemetry_ms is not None:
        lines.extend([f"# TYPE {prefix}_telemetry_stale_ms gauge", f"{prefix}_telemetry_stale_ms {int(snapshot.stale_telemetry_ms)}"])
    return "\n".join(lines) + "\n"
