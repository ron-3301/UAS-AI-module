from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from uas_ai_module.detection.detector import MockDetector
from uas_ai_module.health import HealthThresholds
from uas_ai_module.ingestion.telemetry_parser import MockTelemetrySource
from uas_ai_module.models import Detection, Frame
from uas_ai_module.output.json_serializer import JsonAdvisorySerializer
from uas_ai_module.pipeline import Pipeline


class StaleFrameSource:
    def read(self) -> Frame:
        return Frame(
            "stale-frame",
            datetime.now(timezone.utc) - timedelta(seconds=5),
            100,
            100,
            np.zeros((100, 100, 3), dtype=np.uint8),
        )


def test_stale_frame_invalidates_emitted_detections() -> None:
    pipeline = Pipeline(
        frame_source=StaleFrameSource(),
        telemetry_source=MockTelemetrySource(),
        detector=MockDetector((Detection("Vehicle-Wheeled", 0.9, (10, 10, 40, 40)),)),
        health_thresholds=HealthThresholds(max_frame_stale_ms=1000),
    )
    packet = pipeline.run_once().advisory
    assert packet["health"]["status"] == "degraded"
    row = packet["detections"][0]
    assert row["validity_flag"] is False
    assert "stale_frame" in row["safety_filters_triggered"]


def test_recommendations_are_forced_to_advisory_only() -> None:
    serializer = JsonAdvisorySerializer("test-uas")
    telemetry = MockTelemetrySource().read()
    packet = serializer.packet(
        (),
        telemetry,
        recommendations=[{"recommendation_type": "observe", "advisory_only": False, "validity_flag": True}],
    )
    assert packet["recommendations"][0]["advisory_only"] is True
