from __future__ import annotations

from datetime import datetime, timezone

from uas_ai_module.models import Detection, EnrichedDetection, GeoPoint, HealthStatus, Telemetry
from uas_ai_module.output.json_serializer import JsonAdvisorySerializer


def telemetry(agl: float = 120.0) -> Telemetry:
    return Telemetry(
        timestamp_utc=datetime.now(timezone.utc),
        lat_deg=28.0,
        lon_deg=77.0,
        alt_msl_m=300.0,
        alt_agl_m=agl,
    )


def packet_for(*items: EnrichedDetection, agl: float = 120.0) -> dict:
    serializer = JsonAdvisorySerializer(uas_id="test-uas")
    return serializer.packet(tuple(items), telemetry(agl), HealthStatus(), frame_id="frame-1")


def enriched(detection: Detection, cep_m: float = 5.0) -> EnrichedDetection:
    return EnrichedDetection(
        detection=detection,
        geolocation=GeoPoint(28.0, 77.0, alt_msl_m=180.0, cep_m=cep_m),
        source_uas_ids=("test-uas",),
    )


def test_advisory_only_is_always_true() -> None:
    item = enriched(Detection("Vehicle-Wheeled", 0.8, (1, 2, 3, 4)))
    packet = packet_for(item)
    assert packet["advisory_only"] is True


def test_low_confidence_detection_is_dropped() -> None:
    item = enriched(Detection("Vehicle-Wheeled", 0.29, (1, 2, 3, 4)))
    packet = packet_for(item)
    assert packet["detections"] == []
    assert any("low_detection_confidence" in warning for warning in packet["health"]["warnings"])


def test_civilian_identification_is_suppressed() -> None:
    item = enriched(
        Detection(
            "Vehicle-Wheeled",
            0.9,
            (1, 2, 3, 4),
            sublabel="Civilian-Sedan",
            id_confidence=0.90,
            is_civilian=True,
        )
    )
    packet = packet_for(item)
    assert packet["detections"] == []
    assert any("civilian_suppression" in warning for warning in packet["health"]["warnings"])


def test_person_below_30m_agl_is_dropped() -> None:
    item = enriched(Detection("Person", 0.9, (1, 2, 3, 4)))
    packet = packet_for(item, agl=20.0)
    assert packet["detections"] == []
    assert any("person_below_min_agl" in warning for warning in packet["health"]["warnings"])


def test_large_cep_invalidates_but_does_not_drop() -> None:
    item = enriched(Detection("Vehicle-Tracked", 0.9, (1, 2, 3, 4)), cep_m=30.0)
    packet = packet_for(item)
    assert len(packet["detections"]) == 1
    row = packet["detections"][0]
    assert row["validity_flag"] is False
    assert row["validity_reason"] == "cep_too_large"
    assert "cep_too_large" in row["safety_filters_triggered"]
