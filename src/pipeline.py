from __future__ import annotations

# --- OLD CODE FROM SRC ---
from typing import Dict, Any
import numpy as np
from src.ingestion.frame_capture import FrameCapture
from src.ingestion.telemetry_parser import TelemetryParser
from src.detection.yolo_wrapper import TensorRTDetector
from src.identification.crop_extractor import extract_crops
from src.identification.classifier import TensorRTClassifier
from src.identification.threat_scorer import compute_threat
from src.geolocation.raycaster import estimate_geolocation
from src.output.json_serializer import serialize

class Pipeline:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.capture = FrameCapture("mock")
        self.telemetry = TelemetryParser()
        self.detector = TensorRTDetector(config.get("detection", {}).get("engine_path", "models/detector.engine"), config["detection"]["conf_threshold"])
        self.classifier = TensorRTClassifier(config.get("identification", {}).get("engine_path", "models/classifier.engine"))
        self.mission_id = config["mission_id"]

    def process_frame(self, frame: np.ndarray = None) -> Dict[str, Any]:
        if frame is None: frame = self.capture.read()
        telemetry = self.telemetry.parse({})
        dets = self.detector.predict(frame)
        dets = self.detector.update(dets)
        crops = extract_crops(frame, dets)
        id_results = self.classifier.predict(crops)
        threat_scores = [compute_threat(d, idr) for d, idr in zip(dets, id_results)]
        geo_results = [estimate_geolocation(d, telemetry, {}) for d in dets]
        packet = serialize(self.mission_id, getattr(self.capture, "frame_id", 1), telemetry, dets, id_results, geo_results, threat_scores)
        return packet
# --- END OLD CODE ---

"""End-to-end advisory pipeline orchestration."""


from dataclasses import replace
import time

from detection.detector import Detector, MockDetector
from geolocation.raycaster import GroundPlaneRaycaster
from health import HealthThresholds, evaluate_runtime_health
from identification.classifier import Classifier
from identification.crop_extractor import extract_crop
from ingestion.frame_capture import FrameSource, MockFrameSource
from ingestion.replay import ReplayDataset, ReplayFrameSource, ReplayTelemetrySource
from ingestion.telemetry_parser import MockTelemetrySource, TelemetrySource
from models import CameraIntrinsics, EnrichedDetection, GeoPoint, PipelineResult
from output.json_serializer import JsonAdvisorySerializer
from tracking.track_manager import TrackManager


class Pipeline:
    """Wire frame ingestion, telemetry, detection, geolocation, and output."""

    def __init__(
        self,
        *,
        frame_source: FrameSource | None = None,
        telemetry_source: TelemetrySource | None = None,
        detector: Detector | None = None,
        classifier: Classifier | None = None,
        tracker: TrackManager | None = None,
        raycaster: GroundPlaneRaycaster | None = None,
        serializer: JsonAdvisorySerializer | None = None,
        mission_profile: str = "unknown",
        health_thresholds: HealthThresholds = HealthThresholds(),
    ) -> None:
        self.frame_source = frame_source or MockFrameSource()
        self.telemetry_source = telemetry_source or MockTelemetrySource()
        self.detector = detector or MockDetector()
        self.classifier = classifier
        self.tracker = tracker
        self.raycaster = raycaster
        self.serializer = serializer or JsonAdvisorySerializer()
        self.mission_profile = mission_profile
        self.health_thresholds = health_thresholds

    @classmethod
    def dry_run(cls, uas_id: str = "uas-dry-run") -> "Pipeline":
        """Construct a deterministic dry-run pipeline."""

        return cls(serializer=JsonAdvisorySerializer(uas_id=uas_id), mission_profile="wide_area")


    @classmethod
    def replay(cls, manifest_path: str, uas_id: str = "uas-replay") -> "Pipeline":
        """Construct a deterministic replay pipeline from a mission manifest."""

        dataset = ReplayDataset.from_manifest(manifest_path)
        return cls(
            frame_source=ReplayFrameSource(dataset),
            telemetry_source=ReplayTelemetrySource(dataset),
            detector=MockDetector(),
            tracker=TrackManager(),
            serializer=JsonAdvisorySerializer(uas_id=uas_id),
            mission_profile="replay",
        )

    def run_once(self) -> PipelineResult:
        """Run one pipeline iteration and return a structured result."""

        start = time.perf_counter()
        warnings: list[str] = []

        frame = self.frame_source.read()
        telemetry = self.telemetry_source.read()
        raycaster = self.raycaster or GroundPlaneRaycaster(_default_intrinsics(frame.width, frame.height))

        try:
            raw_detections = self.detector.detect(frame)
        except Exception as exc:
            raw_detections = ()
            warnings.append(f"detector_failed: {exc}")

        enriched = []
        if self.tracker is not None:
            raw_detections = self.tracker.update(tuple(raw_detections))

        for detection in raw_detections:
            classified_detection = detection
            if self.classifier is not None:
                try:
                    crop = extract_crop(frame, detection, padding_px=2)
                    classification = self.classifier.classify(crop)
                    classified_detection = replace(
                        detection,
                        sublabel=classification.sublabel,
                        id_confidence=classification.confidence,
                        is_civilian=classification.is_civilian,
                    )
                except Exception as exc:
                    warnings.append(f"classification_failed: {exc}")

            try:
                geo = raycaster.geolocate(classified_detection, frame, telemetry)
            except Exception as exc:  # defensive fail-closed path
                geo = GeoPoint(None, None, valid=False, reason=f"geolocation_exception: {exc}")
            enriched.append(
                EnrichedDetection(
                    detection=classified_detection,
                    geolocation=geo,
                    prediction=None,
                    risk_score=None,
                    source_uas_ids=(self.serializer.uas_id,),
                )
            )

        latency_ms = (time.perf_counter() - start) * 1000.0
        health = evaluate_runtime_health(
            frame,
            telemetry,
            thresholds=self.health_thresholds,
            base_warnings=tuple(warnings),
            latency_ms=latency_ms,
        )
        detections = tuple(enriched)
        advisory = self.serializer.packet(
            detections,
            telemetry,
            health,
            frame_id=frame.frame_id,
            timestamp_utc=frame.timestamp_utc,
            mission_profile=self.mission_profile,
        )
        return PipelineResult(frame, telemetry, detections, health, advisory)


def _default_intrinsics(width: int, height: int) -> CameraIntrinsics:
    # A reasonable synthetic pinhole calibration for dry-run. Real deployments
    # must load calibrated intrinsics from a schema-validated camera file.
    fx = float(max(width, height))
    fy = fx
    return CameraIntrinsics(
        camera_id="mock-cam",
        width=width,
        height=height,
        fx=fx,
        fy=fy,
        cx=width / 2.0,
        cy=height / 2.0,
        mount_roll_deg=0.0,
        mount_pitch_deg=-90.0,
        mount_yaw_deg=0.0,
    )
