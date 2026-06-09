# locks the safety contract from dec-003 and docs/12 §2.
from __future__ import annotations

import json

from src.output.json_serializer import (
    CIVILIAN_ID_CONF_DROP,
    MIN_DETECTION_CONF,
    Detection,
    Packet,
    build_packet,
    to_json_bytes,
)


def _base_packet(dets):
    return Packet(
        schema_version="1.0",
        mission_id="MSN-TEST-001",
        frame_id=1,
        timestamp_utc="2026-06-08T12:00:00Z",
        uas_telemetry={"lat": 0.0, "lon": 0.0, "alt_agl_m": 100.0},
        detections=dets,
    )


def test_low_confidence_dropped() -> None:
    d = Detection(
        detection_id="d1", track_id=None, bbox_px=(0, 0, 10, 10),
        detection_class="Vehicle-Wheeled",
        detection_confidence=MIN_DETECTION_CONF - 0.01,
    )
    out, suppressed = build_packet(_base_packet([d]), alt_agl_m=100.0)
    assert out["detections"] == []
    assert suppressed == [("d1", "below_min_detection_conf")]


def test_civilian_suppressed() -> None:
    d = Detection(
        detection_id="d2", track_id=None, bbox_px=(0, 0, 10, 10),
        detection_class="Vehicle-Wheeled", detection_confidence=0.99,
        identification={"label": "Civilian-Sedan", "confidence": CIVILIAN_ID_CONF_DROP + 0.01},
    )
    out, suppressed = build_packet(_base_packet([d]), alt_agl_m=100.0)
    assert out["detections"] == []
    assert suppressed[0][1] == "civilian_identified"


def test_low_altitude_person_suppressed() -> None:
    d = Detection(
        detection_id="d3", track_id=None, bbox_px=(0, 0, 10, 10),
        detection_class="Person", detection_confidence=0.95,
    )
    out, suppressed = build_packet(_base_packet([d]), alt_agl_m=20.0)
    assert out["detections"] == []
    assert suppressed[0][1] == "person_below_min_altitude"


def test_high_cep_marks_invalid_but_keeps_detection() -> None:
    d = Detection(
        detection_id="d4", track_id=7, bbox_px=(0, 0, 10, 10),
        detection_class="Vehicle-Tracked", detection_confidence=0.90,
        identification={"label": "T-72", "confidence": 0.8},
        geolocation={"lat": 1.0, "lon": 2.0, "cep_m": 30.0},
        threat_score=0.7,
    )
    out, suppressed = build_packet(_base_packet([d]), alt_agl_m=120.0)
    assert len(out["detections"]) == 1
    assert out["validity_flag"] is False
    assert suppressed == []


def test_legitimate_detection_passes_through() -> None:
    d = Detection(
        detection_id="d5", track_id=17, bbox_px=(842, 391, 122, 56),
        detection_class="Vehicle-Wheeled", detection_confidence=0.91,
        identification={"label": "Humvee", "confidence": 0.84},
        geolocation={"lat": 51.5076, "lon": -0.1280, "cep_m": 3.8},
        threat_score=0.61,
    )
    out, _ = build_packet(_base_packet([d]), alt_agl_m=98.7)
    assert len(out["detections"]) == 1
    blob = json.loads(to_json_bytes(out))
    assert blob["detections"][0]["identification"]["label"] == "Humvee"
    assert blob["validity_flag"] is True
