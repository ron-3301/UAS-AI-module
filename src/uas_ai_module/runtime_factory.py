"""Factory helpers for constructing runtime components from validated config."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from uas_ai_module.detection.detector import MockDetector
from uas_ai_module.detection.onnx_detector import OnnxDetector, OnnxDetectorConfig
from uas_ai_module.detection.tensorrt_detector import TensorRtDetector
from uas_ai_module.health import HealthThresholds
from uas_ai_module.ingestion.camera import OpenCvCameraSource
from uas_ai_module.ingestion.frame_capture import MockFrameSource
from uas_ai_module.ingestion.mavlink import MavlinkTelemetrySource
from uas_ai_module.ingestion.telemetry_parser import MockTelemetrySource
from uas_ai_module.output.json_serializer import JsonAdvisorySerializer
from uas_ai_module.tracking.track_manager import TrackManager


class RuntimeFactoryError(ValueError):
    """Raised when config cannot be converted into runtime components."""


def build_detector_from_config(config: dict[str, Any], *, allow_mock: bool = False):
    """Build a detector from runtime config.

    `allow_mock=True` is for local smoke tests only. Without it, runtime model
    artifacts must be real `.onnx` or `.engine` paths.
    """

    if allow_mock:
        return MockDetector()

    model = config.get("model", {})
    weights = str(model.get("detection_weights", ""))
    suffix = Path(weights).suffix.lower()
    if suffix == ".onnx":
        input_size = int(model.get("detection_input_size", 640))
        return OnnxDetector(
            OnnxDetectorConfig(
                model_path=weights,
                input_width=input_size,
                input_height=input_size,
                conf_threshold=float(model.get("detection_conf_threshold", 0.30)),
                iou_threshold=float(model.get("detection_iou_threshold", 0.45)),
                metadata_path=model.get("detection_metadata"),
            )
        )
    if suffix == ".engine":
        return TensorRtDetector(weights)
    raise RuntimeFactoryError(f"unsupported detection runtime artifact: {weights}")


def build_frame_source_from_config(config: dict[str, Any], *, allow_mock: bool = False):
    sensor = config.get("sensor", {})
    source = str(sensor.get("source", "mock"))
    if source == "mock" or allow_mock:
        return MockFrameSource()
    return OpenCvCameraSource(source)


def build_telemetry_source_from_config(config: dict[str, Any], *, allow_mock: bool = False):
    telemetry = config.get("telemetry", {})
    source = str(telemetry.get("source", "mock"))
    if source == "mock" or allow_mock:
        return MockTelemetrySource()
    if source == "mavlink":
        port = int(telemetry.get("udp_port", 14550))
        return MavlinkTelemetrySource(endpoint=f"udp:0.0.0.0:{port}")
    raise RuntimeFactoryError(f"unsupported telemetry source: {source}")


def build_pipeline_from_config(
    config: dict[str, Any],
    *,
    uas_id: str,
    allow_mock_backends: bool = False,
):
    """Build a one-pass runtime pipeline from validated config."""

    from uas_ai_module.pipeline import Pipeline

    telemetry_cfg = config.get("telemetry", {})
    max_stale_ms = int(telemetry_cfg.get("max_stale_ms", 1000))
    return Pipeline(
        frame_source=build_frame_source_from_config(config, allow_mock=allow_mock_backends),
        telemetry_source=build_telemetry_source_from_config(config, allow_mock=allow_mock_backends),
        detector=build_detector_from_config(config, allow_mock=allow_mock_backends),
        tracker=TrackManager(),
        serializer=JsonAdvisorySerializer(uas_id=uas_id),
        mission_profile=str(config.get("mission_profile", "unknown")),
        health_thresholds=HealthThresholds(
            max_frame_stale_ms=max_stale_ms,
            max_telemetry_stale_ms=max_stale_ms,
        ),
    )
