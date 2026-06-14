from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from uas_ai_module.detection.detector import RuntimeModelConfigError
from uas_ai_module.detection.nms import BoxCandidate, box_iou, nms
from uas_ai_module.detection.onnx_detector import OnnxDetector, OnnxDetectorConfig
from uas_ai_module.detection.tensorrt_detector import TensorRtDetector
from uas_ai_module.models import Frame


@dataclass
class FakeIO:
    name: str


class FakeDetectionSession:
    def __init__(self, output: np.ndarray) -> None:
        self.output = output
        self.last_feed = None

    def get_inputs(self):
        return [FakeIO("images")]

    def get_outputs(self):
        return [FakeIO("output0")]

    def run(self, output_names, feed):
        assert output_names == ["output0"]
        assert "images" in feed
        self.last_feed = feed["images"]
        return [self.output]


def frame() -> Frame:
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    return Frame("frame", __import__("datetime").datetime.now(__import__("datetime").timezone.utc), 640, 480, image)


def test_iou_and_nms_suppresses_same_class_overlap() -> None:
    assert box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    candidates = [
        BoxCandidate(0, 0, 100, 100, 0.90, 1),
        BoxCandidate(5, 5, 105, 105, 0.80, 1),
        BoxCandidate(5, 5, 105, 105, 0.70, 2),
    ]
    kept = nms(candidates, iou_threshold=0.5, class_agnostic=False)
    assert len(kept) == 2
    assert kept[0].score == 0.90
    assert {item.class_id for item in kept} == {1, 2}


def test_onnx_detector_decodes_xyxy_output_and_runs_nms() -> None:
    output = np.array(
        [
            [
                [100.0, 100.0, 200.0, 200.0, 0.90, 1.0],
                [105.0, 105.0, 205.0, 205.0, 0.80, 1.0],
                [300.0, 100.0, 380.0, 180.0, 0.20, 1.0],
            ]
        ],
        dtype=np.float32,
    )
    session = FakeDetectionSession(output)
    detector = OnnxDetector(
        OnnxDetectorConfig(
            model_path="detector.onnx",
            input_width=640,
            input_height=480,
            conf_threshold=0.30,
            iou_threshold=0.50,
        ),
        session=session,
    )
    detections = detector.detect(frame())
    assert session.last_feed is not None
    assert session.last_feed.shape == (1, 3, 480, 640)
    assert len(detections) == 1
    assert detections[0].class_label == "Vehicle-Wheeled"
    assert detections[0].confidence == pytest.approx(0.90, abs=1e-6)


def test_onnx_detector_decodes_cxcywh_class_scores() -> None:
    # cx, cy, w, h, obj, class0, class1, class2...
    output = np.array([[[0.5, 0.5, 0.2, 0.2, 0.9, 0.1, 0.8, 0.1]]], dtype=np.float32)
    detector = OnnxDetector(
        OnnxDetectorConfig(model_path="detector.onnx", input_width=640, input_height=480),
        session=FakeDetectionSession(output),
    )
    detections = detector.detect(frame())
    assert len(detections) == 1
    assert detections[0].class_label == "Vehicle-Wheeled"
    assert detections[0].confidence == pytest.approx(0.72, abs=1e-6)
    x1, y1, x2, y2 = detections[0].bbox_xyxy
    assert 250 < x1 < 270
    assert 190 < y1 < 200
    assert 370 < x2 < 390
    assert 280 < y2 < 290


def test_onnx_detector_rejects_pt_artifact() -> None:
    with pytest.raises(RuntimeModelConfigError):
        OnnxDetectorConfig(model_path="bad.pt").validate()


def test_tensorrt_detector_validates_engine_suffix() -> None:
    detector = TensorRtDetector(Path("detector.engine"))
    assert detector.engine_path.suffix == ".engine"
    with pytest.raises(RuntimeModelConfigError):
        TensorRtDetector("detector.onnx")
