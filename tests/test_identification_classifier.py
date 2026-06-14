from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from uas_ai_module.detection.detector import RuntimeModelConfigError
from uas_ai_module.identification.classifier import (
    Classification,
    MockClassifier,
    OnnxClassifier,
    OnnxClassifierConfig,
)


@dataclass
class FakeIO:
    name: str


class FakeClassifierSession:
    def __init__(self, logits: np.ndarray) -> None:
        self.logits = logits

    def get_inputs(self):
        return [FakeIO("crop")]

    def get_outputs(self):
        return [FakeIO("logits")]

    def run(self, output_names, feed):
        assert output_names == ["logits"]
        assert feed["crop"].shape == (1, 3, 224, 224)
        return [self.logits]


def test_mock_classifier_returns_configured_result() -> None:
    result = Classification("Civilian-Sedan", 0.9, True)
    classifier = MockClassifier(result)
    assert classifier.classify(np.zeros((10, 10, 3), dtype=np.uint8)) == result


def test_onnx_classifier_returns_label_and_civilian_flag() -> None:
    session = FakeClassifierSession(np.array([[0.1, 3.0, 0.2]], dtype=np.float32))
    classifier = OnnxClassifier(
        OnnxClassifierConfig(
            model_path="classifier.onnx",
            labels=("Unknown", "Civilian-Sedan", "T-72"),
        ),
        session=session,
    )
    result = classifier.classify(np.zeros((32, 32, 3), dtype=np.uint8))
    assert result.sublabel == "Civilian-Sedan"
    assert result.confidence > 0.8
    assert result.is_civilian is True


def test_onnx_classifier_rejects_pt_artifact() -> None:
    with pytest.raises(RuntimeModelConfigError):
        OnnxClassifierConfig("classifier.pt").validate()
