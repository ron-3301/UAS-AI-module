"""Advisory JSON serialization with hard-coded safety filters.

These filters are intentionally constants in code, not configuration values:

- Detection confidence must be at least 0.30 to be emitted.
- Civilian identifications with identity confidence above 0.50 are suppressed.
- Person detections below 30 m AGL are suppressed.
- CEP above 25 m marks the detection invalid.

The serializer emits advisory/status data only. It does not emit commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from uas_ai_module.models import EnrichedDetection, HealthStatus, Telemetry


@dataclass(frozen=True)
class SafetyFilterConstants:
    """Non-configurable safety constants."""

    min_detection_confidence: float = 0.30
    civilian_suppression_id_confidence: float = 0.50
    min_person_agl_m: float = 30.0
    max_valid_cep_m: float = 25.0


class JsonAdvisorySerializer:
    """Serialize enriched detections into versioned advisory JSON packets."""

    schema_version = "1.1"

    def __init__(self, uas_id: str = "uas-local") -> None:
        if not uas_id:
            raise ValueError("uas_id must be non-empty")
        self.uas_id = uas_id
        self.constants = SafetyFilterConstants()

    def packet(
        self,
        detections: tuple[EnrichedDetection, ...],
        telemetry: Telemetry,
        health: HealthStatus | None = None,
        *,
        frame_id: str | int | None = None,
        timestamp_utc: datetime | None = None,
        mission_profile: str = "unknown",
        recommendations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build an advisory packet dictionary."""

        health = health or HealthStatus()
        timestamp_utc = timestamp_utc or datetime.now(timezone.utc)

        emitted: list[dict[str, Any]] = []
        warnings = list(health.warnings)
        packet_level_filters = _packet_level_filters(health)
        dropped_counts = {
            "low_detection_confidence": 0,
            "civilian_suppression": 0,
            "person_below_min_agl": 0,
        }

        for enriched in detections:
            row, dropped_reason = self._serialize_detection(
                enriched,
                telemetry,
                packet_level_filters=packet_level_filters,
            )
            if row is None:
                if dropped_reason:
                    dropped_counts[dropped_reason] += 1
                continue
            emitted.append(row)

        for reason, count in dropped_counts.items():
            if count:
                warnings.append(f"{reason}: dropped {count} detection(s)")

        status = health.status
        if warnings and status == "ok":
            status = "degraded"

        packet = {
            "schema_version": self.schema_version,
            "timestamp_utc": _isoformat_z(timestamp_utc),
            "uas_id": self.uas_id,
            "frame_id": frame_id,
            "advisory_only": True,
            "mission_profile": mission_profile,
            "health": {
                "status": status,
                "warnings": warnings,
                "latency_ms": health.latency_ms,
                "camera_stale_ms": health.camera_stale_ms,
                "telemetry_stale_ms": health.telemetry_stale_ms,
                "temperature_c": health.temperature_c,
                "power_w": health.power_w,
            },
            "ownship": {
                "lat": telemetry.lat_deg,
                "lon": telemetry.lon_deg,
                "alt_msl_m": telemetry.alt_msl_m,
                "alt_agl_m": telemetry.alt_agl_m,
                "heading_deg": telemetry.yaw_deg,
            },
            "detections": emitted,
            "recommendations": _sanitize_recommendations(recommendations or []),
        }
        return packet

    def dumps(self, packet: dict[str, Any], *, indent: int | None = None) -> str:
        """Serialize a packet to JSON."""

        return json.dumps(packet, indent=indent, sort_keys=True)

    def _serialize_detection(
        self,
        enriched: EnrichedDetection,
        telemetry: Telemetry,
        *,
        packet_level_filters: tuple[str, ...] = (),
    ) -> tuple[dict[str, Any] | None, str | None]:
        detection = enriched.detection
        detection.validate()

        if detection.confidence < self.constants.min_detection_confidence:
            return None, "low_detection_confidence"

        if _is_suppressed_civilian(detection, self.constants):
            return None, "civilian_suppression"

        if (
            detection.class_label == "Person"
            and telemetry.alt_agl_m is not None
            and telemetry.alt_agl_m < self.constants.min_person_agl_m
        ):
            return None, "person_below_min_agl"

        filters = []
        validity_flag = True
        validity_reason = "ok"

        geolocation = enriched.geolocation
        if geolocation is not None:
            if not geolocation.valid:
                filters.append("invalid_geolocation")
                validity_flag = False
                validity_reason = geolocation.reason or "invalid_geolocation"
            elif geolocation.cep_m is not None and geolocation.cep_m > self.constants.max_valid_cep_m:
                filters.append("cep_too_large")
                validity_flag = False
                validity_reason = "cep_too_large"

        for packet_filter in packet_level_filters:
            if packet_filter not in filters:
                filters.append(packet_filter)
            validity_flag = False
            if validity_reason == "ok":
                validity_reason = packet_filter

        if not filters:
            filters = ["none"]

        prediction = enriched.prediction
        return {
            "track_id": detection.track_id,
            "global_track_id": None,
            "class_label": detection.class_label,
            "confidence": detection.confidence,
            "bbox_xyxy": list(detection.bbox_xyxy),
            "identification": {
                "sublabel": detection.sublabel,
                "confidence": detection.id_confidence,
                "is_civilian": detection.is_civilian,
            },
            "geolocation": {
                "lat": geolocation.lat_deg if geolocation else None,
                "lon": geolocation.lon_deg if geolocation else None,
                "alt_msl_m": geolocation.alt_msl_m if geolocation else None,
                "cep_m": geolocation.cep_m if geolocation else None,
                "covariance": list(geolocation.covariance) if geolocation and geolocation.covariance else None,
            },
            "prediction": {
                "intent": prediction.intent if prediction else None,
                "intent_confidence": prediction.intent_confidence if prediction else None,
                "tcpa_s": prediction.tcpa_s if prediction else None,
                "closest_approach_m": prediction.closest_approach_m if prediction else None,
            },
            "risk_score": enriched.risk_score,
            "validity_flag": validity_flag,
            "validity_reason": validity_reason,
            "safety_filters_triggered": filters,
            "source_uas_ids": list(enriched.source_uas_ids),
        }, None


def _is_suppressed_civilian(detection: Any, constants: SafetyFilterConstants) -> bool:
    id_conf = detection.id_confidence
    if id_conf is None or id_conf <= constants.civilian_suppression_id_confidence:
        return False
    sublabel = (detection.sublabel or "").lower()
    explicit_civilian = detection.is_civilian is True or sublabel.startswith("civilian")
    return explicit_civilian


def _packet_level_filters(health: HealthStatus) -> tuple[str, ...]:
    filters = []
    joined = "\n".join(health.warnings).lower()
    if "stale_telemetry" in joined:
        filters.append("stale_telemetry")
    if "stale_frame" in joined:
        filters.append("stale_frame")
    if "invalid_calibration" in joined:
        filters.append("invalid_calibration")
    return tuple(filters)


def _sanitize_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for recommendation in recommendations:
        item = dict(recommendation)
        item["advisory_only"] = True
        sanitized.append(item)
    return sanitized


def _isoformat_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")
