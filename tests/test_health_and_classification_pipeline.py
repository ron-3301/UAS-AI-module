from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from uas_ai_module.detection.detector import MockDetector
from uas_ai_module.health import HealthThresholds, staleness_ms
from uas_ai_module.identification.classifier import Classification, MockClassifier
from uas_ai_module.identification.crop_extractor import extract_crop
from uas_ai_module.ingestion.telemetry_parser import MockTelemetrySource
from uas_ai_module.models import Detection, Frame, Telemetry
from uas_ai_module.pipeline import Pipeline


class NumpyFrameSource:
    def __init__(self, timestamp: datetime | None = None) -> None:
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def read(self) -> Frame:
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        image[10:40, 20:60] = 255
        return Frame("np-frame", self.timestamp, 100, 100, image)


class StaleTelemetrySource:
    def read(self) -> Telemetry:
        return Telemetry(
            timestamp_utc=datetime.now(timezone.utc) - timedelta(seconds=5),
            lat_deg=28.0,
            lon_deg=77.0,
            alt_msl_m=300.0,
            alt_agl_m=120.0,
        )


def test_staleness_ms_is_non_negative() -> None:
    now = datetime.now(timezone.utc)
    assert staleness_ms(now + timedelta(seconds=1), now=now) == 0
    assert 900 <= staleness_ms(now - timedelta(seconds=1), now=now) <= 1000


def test_crop_extractor_clips_to_image_bounds() -> None:
    frame = NumpyFrameSource().read()
    detection = Detection("Vehicle-Wheeled", 0.9, (-10.0, 5.0, 30.0, 30.0))
    crop = extract_crop(frame, detection)
    assert crop.shape == (25, 30, 3)


def test_classifier_result_is_applied_and_civilian_suppressed() -> None:
    detector = MockDetector((Detection("Vehicle-Wheeled", 0.9, (20, 10, 60, 40)),))
    classifier = MockClassifier(Classification("Civilian-Sedan", 0.95, True))
    pipeline = Pipeline(
        frame_source=NumpyFrameSource(),
        telemetry_source=MockTelemetrySource(),
        detector=detector,
        classifier=classifier,
    )
    packet = pipeline.run_once().advisory
    assert packet["detections"] == []
    assert any("civilian_suppression" in warning for warning in packet["health"]["warnings"])


def test_stale_telemetry_invalidates_emitted_detections() -> None:
    detector = MockDetector((Detection("Vehicle-Wheeled", 0.9, (20, 10, 60, 40)),))
    pipeline = Pipeline(
        frame_source=NumpyFrameSource(),
        telemetry_source=StaleTelemetrySource(),
        detector=detector,
        health_thresholds=HealthThresholds(max_telemetry_stale_ms=1000),
    )
    packet = pipeline.run_once().advisory
    assert packet["health"]["status"] == "degraded"
    assert "stale_telemetry" in packet["detections"][0]["safety_filters_triggered"]
    assert packet["detections"][0]["validity_flag"] is False
