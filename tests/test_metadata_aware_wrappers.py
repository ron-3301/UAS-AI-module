from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from uas_ai_module.detection.detector import RuntimeModelConfigError
from uas_ai_module.detection.onnx_detector import OnnxDetector, OnnxDetectorConfig
from uas_ai_module.identification.classifier import OnnxClassifier, OnnxClassifierConfig


@dataclass
class FakeIO:
    name: str


class FakeDetectionSession:
    def get_inputs(self):
        return [FakeIO("images")]

    def get_outputs(self):
        return [FakeIO("output0")]

    def run(self, output_names, feed):
        return [np.array([[[0.1, 0.1, 0.2, 0.2, 0.9, 0.1, 0.8]]], dtype=np.float32)]


class FakeClassifierSession:
    def get_inputs(self):
        return [FakeIO("crop")]

    def get_outputs(self):
        return [FakeIO("logits")]

    def run(self, output_names, feed):
        return [np.array([[0.1, 4.0]], dtype=np.float32)]


def write_metadata(tmp_path: Path, *, role: str, artifact: str, shape: list[int], classes: list[str]) -> Path:
    path = tmp_path / f"{role}.metadata.json"
    path.write_text(json.dumps({
        "name": f"{role}-test",
        "role": role,
        "artifact": artifact,
        "sha256": "0" * 64,
        "backend": "onnxruntime",
        "input": {"name": "input", "shape": shape, "dtype": "float32"},
        "outputs": [{"name": "output0"}],
        "class_names": classes,
    }))
    return path


def test_onnx_detector_uses_metadata_class_names(tmp_path: Path) -> None:
    metadata = write_metadata(
        tmp_path,
        role="detector",
        artifact="detector.onnx",
        shape=[1, 3, 640, 640],
        classes=["Person", "Vehicle-Tracked"],
    )
    detector = OnnxDetector(
        OnnxDetectorConfig(model_path="detector.onnx", metadata_path=metadata),
        session=FakeDetectionSession(),
    )
    from uas_ai_module.models import Frame
    import datetime as dt

    image = np.zeros((640, 640, 3), dtype=np.uint8)
    detections = detector.detect(Frame("f", dt.datetime.now(dt.timezone.utc), 640, 640, image))
    assert detections[0].class_label == "Vehicle-Tracked"


def test_onnx_detector_rejects_metadata_shape_mismatch(tmp_path: Path) -> None:
    metadata = write_metadata(
        tmp_path,
        role="detector",
        artifact="detector.onnx",
        shape=[1, 3, 320, 320],
        classes=["Person"],
    )
    with pytest.raises(RuntimeModelConfigError, match="input shape"):
        OnnxDetectorConfig(model_path="detector.onnx", metadata_path=metadata).validate()


def test_onnx_classifier_uses_metadata_labels(tmp_path: Path) -> None:
    metadata = write_metadata(
        tmp_path,
        role="classifier",
        artifact="classifier.onnx",
        shape=[1, 3, 224, 224],
        classes=["Unknown", "Civilian-Sedan"],
    )
    classifier = OnnxClassifier(
        OnnxClassifierConfig(model_path="classifier.onnx", metadata_path=metadata),
        session=FakeClassifierSession(),
    )
    result = classifier.classify(np.zeros((16, 16, 3), dtype=np.uint8))
    assert result.sublabel == "Civilian-Sedan"
    assert result.is_civilian is True
