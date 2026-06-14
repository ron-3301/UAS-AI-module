"""Detector interfaces and runtime artifact validation."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from uas_ai_module.models import Detection, Frame


class RuntimeModelConfigError(ValueError):
    """Raised when a runtime model artifact violates deployment constraints."""


RUNTIME_MODEL_SUFFIXES = {".onnx", ".engine"}
FORBIDDEN_RUNTIME_SUFFIXES = {".pt", ".pth"}


def validate_runtime_model_path(path: str | Path) -> Path:
    """Validate a model path for Jetson runtime inference.

    PyTorch checkpoint files are intentionally rejected. Training/export code may
    consume `.pt` files, but the runtime detector/classifier must not.
    """

    model_path = Path(path)
    suffix = model_path.suffix.lower()
    if suffix in FORBIDDEN_RUNTIME_SUFFIXES:
        raise RuntimeModelConfigError(
            f"{model_path} is a training checkpoint, not a runtime artifact; use .onnx or .engine"
        )
    if suffix not in RUNTIME_MODEL_SUFFIXES:
        raise RuntimeModelConfigError(
            f"unsupported runtime model suffix {suffix!r}; expected one of {sorted(RUNTIME_MODEL_SUFFIXES)}"
        )
    return model_path


class Detector(Protocol):
    """Object detector interface."""

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        """Return detections for one frame."""


class MockDetector:
    """Deterministic detector used for dry-run and tests.

    This is not a fake production model. It exists so the pipeline, safety
    filters, schemas, and deployment checks can be exercised without camera or
    GPU hardware.
    """

    def __init__(self, detections: tuple[Detection, ...] | None = None) -> None:
        if detections is None:
            detections = (
                Detection(
                    class_label="Vehicle-Wheeled",
                    confidence=0.82,
                    bbox_xyxy=(220.0, 170.0, 330.0, 260.0),
                    track_id="mock-track-1",
                    sublabel="Unknown",
                    id_confidence=0.40,
                    is_civilian=False,
                ),
            )
        for detection in detections:
            detection.validate()
        self._detections = detections

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        _ = frame
        return self._detections


class RuntimeDetectorUnavailable:
    """Explicit placeholder for future ONNX/TensorRT detector integration.

    The class validates the model artifact now and fails with a clear message if
    inference is attempted before a backend implementation is wired in.
    """

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = validate_runtime_model_path(model_path)

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        _ = frame
        raise RuntimeError(
            "runtime detector backend is not wired in this rebuild yet; use MockDetector for dry-run "
            f"or implement ONNX/TensorRT inference for {self.model_path}"
        )
