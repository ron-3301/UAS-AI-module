# end-to-end integration test for the full 5-layer pipeline.
from __future__ import annotations

import importlib.util
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("numpy") is None
    or importlib.util.find_spec("cv2") is None,
    reason="opencv-python or numpy not installed",
)


def _make_frames(n: int) -> Iterator:
    import numpy as np

    from src.types import FramePacket

    for i in range(n):
        img = np.full((480, 640, 3), 60, dtype=np.uint8)
        yield FramePacket(
            frame_id=i,
            timestamp_utc="2026-06-08T12:00:00.000Z",
            image=img,
            telemetry={"lat": 51.5, "lon": -0.12, "alt_agl_m": 120.0,
                       "alt_msl_m": 200.0, "roll": 0, "pitch": -90, "yaw": 0},
            telemetry_stale=False,
            capture_latency_ms=0.0,
        )


def test_pipeline_emits_one_packet_per_frame() -> None:
    from src.detection.yolo_wrapper import MockDetector
    from src.identification.classifier import MockClassifier
    from src.identification.threat_scorer import ThreatScorer
    from src.output.udp_emitter import InMemoryEmitter
    from src.pipeline import Pipeline
    from src.types import RawDetection

    # Scripted detector: one Humvee per frame at a fixed location, slight drift.
    def script(packet):
        x = 100 + packet.frame_id  # drifts 1 px per frame
        return [RawDetection(
            bbox_px=(x, 100, 120, 60),
            detection_class="Vehicle-Wheeled",
            detection_confidence=0.91,
        )]

    # Mock classifier always returns Humvee with high confidence.
    def cls_fn(_crop):
        return ("Humvee", 0.84)

    scorer = ThreatScorer(REPO / "configs" / "class_weights.yaml")
    emitter = InMemoryEmitter()
    cfg = {"model": {"detection_iou_threshold": 0.45, "classifier_input_size": 224},
           "mission_id": "MSN-TEST"}

    pipe = Pipeline(
        cfg=cfg, frame_source=_make_frames(10),
        detector=MockDetector(script),
        classifier=MockClassifier(cls_fn),
        emitter=emitter, threat_scorer=scorer,
    )
    metrics = pipe.run()

    assert metrics.n_frames == 10
    assert len(emitter.packets) == 10
    assert metrics.n_detections_emitted == 10
    # Track id is stable across the 10-frame drift.
    track_ids = {p["detections"][0]["track_id"] for p in emitter.packets}
    assert len(track_ids) == 1
    # Per-stage timing is recorded for every stage.
    for stage in ("detect", "nms_track", "identify", "geolocate", "serialise"):
        assert stage in metrics.cumulative_stage_ms


def test_pipeline_enforces_civilian_suppression_end_to_end() -> None:
    # dec-003: civilian-sedan with id_conf > 0.5 must be suppressed at layer 5.
    from src.detection.yolo_wrapper import MockDetector
    from src.identification.classifier import MockClassifier
    from src.output.udp_emitter import InMemoryEmitter
    from src.pipeline import Pipeline
    from src.types import RawDetection

    def script(packet):
        return [RawDetection(bbox_px=(100, 100, 120, 60),
                              detection_class="Vehicle-Wheeled",
                              detection_confidence=0.95)]

    def cls_fn(_crop):
        return ("Civilian-Sedan", 0.92)

    emitter = InMemoryEmitter()
    pipe = Pipeline(
        cfg={"model": {"detection_iou_threshold": 0.45, "classifier_input_size": 224}},
        frame_source=_make_frames(3),
        detector=MockDetector(script),
        classifier=MockClassifier(cls_fn),
        emitter=emitter,
    )
    metrics = pipe.run()

    assert metrics.n_frames == 3
    # The civilian-sedan should be suppressed at the output layer.
    assert metrics.n_detections_emitted == 0
    assert metrics.n_suppressed == 3
    for pkt in emitter.packets:
        assert pkt["detections"] == []


def test_pipeline_runs_without_classifier_or_scorer() -> None:
    # layer 3 is optional. pipeline must still run and emit packets.
    from src.detection.yolo_wrapper import MockDetector
    from src.output.udp_emitter import InMemoryEmitter
    from src.pipeline import Pipeline
    from src.types import RawDetection

    def script(_p):
        return [RawDetection(bbox_px=(50, 50, 80, 40),
                              detection_class="Aircraft-Fixed",
                              detection_confidence=0.7)]

    emitter = InMemoryEmitter()
    pipe = Pipeline(
        cfg={"model": {"detection_iou_threshold": 0.45}},
        frame_source=_make_frames(2),
        detector=MockDetector(script),
        emitter=emitter,
    )
    metrics = pipe.run()
    assert metrics.n_detections_emitted == 2
    # No classifier ⇒ no "identification" key in output dets.
    for p in emitter.packets:
        for d in p["detections"]:
            assert "identification" not in d
