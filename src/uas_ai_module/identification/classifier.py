"""Runtime classifier boundary for cropped detections."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

import numpy as np

from uas_ai_module.detection.detector import RuntimeModelConfigError, validate_runtime_model_path
from uas_ai_module.model_metadata import ModelMetadataError, load_model_metadata


@dataclass(frozen=True)
class Classification:
    sublabel: str
    confidence: float
    is_civilian: bool | None = None


class Classifier(Protocol):
    def classify(self, crop: np.ndarray) -> Classification:
        """Classify one cropped detection image."""


class MockClassifier:
    def __init__(self, result: Classification | None = None) -> None:
        self.result = result or Classification("Unknown", 0.0, None)

    def classify(self, crop: np.ndarray) -> Classification:
        _ = crop
        return self.result


@dataclass(frozen=True)
class OnnxClassifierConfig:
    model_path: str | Path
    input_width: int = 224
    input_height: int = 224
    labels: tuple[str, ...] = ("Unknown",)
    civilian_labels: tuple[str, ...] = ("Civilian", "Civilian-Sedan", "Civilian-Truck")
    providers: tuple[str, ...] = ("CUDAExecutionProvider", "CPUExecutionProvider")
    metadata_path: str | Path | None = None

    def validate(self) -> None:
        model_path = validate_runtime_model_path(self.model_path)
        if model_path.suffix.lower() != ".onnx":
            raise RuntimeModelConfigError("OnnxClassifier requires a .onnx model artifact")
        if self.input_width <= 0 or self.input_height <= 0:
            raise RuntimeModelConfigError("classifier input dimensions must be positive")
        if not self.labels:
            raise RuntimeModelConfigError("classifier labels must not be empty")
        if self.metadata_path is not None:
            try:
                metadata = load_model_metadata(self.metadata_path, verify_hash=False)
            except ModelMetadataError as exc:
                raise RuntimeModelConfigError(str(exc)) from exc
            if metadata.role != "classifier":
                raise RuntimeModelConfigError("classifier metadata role must be 'classifier'")
            if metadata.backend != "onnxruntime":
                raise RuntimeModelConfigError("ONNX classifier metadata backend must be 'onnxruntime'")
            if Path(metadata.artifact).name != Path(model_path).name:
                raise RuntimeModelConfigError("classifier metadata artifact does not match model_path")
            if len(metadata.input_shape) >= 4:
                if metadata.input_shape[-2] != self.input_height or metadata.input_shape[-1] != self.input_width:
                    raise RuntimeModelConfigError("classifier metadata input shape does not match configured input size")


class OnnxClassifier:
    """ONNX Runtime classifier wrapper with injectable session for tests."""

    def __init__(self, config: OnnxClassifierConfig, *, session: Any | None = None) -> None:
        config.validate()
        self.config = config
        self.model_path = validate_runtime_model_path(config.model_path)
        if session is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"ONNX classifier model not found: {self.model_path}")
            try:
                import onnxruntime as ort  # type: ignore
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "onnxruntime is required to construct OnnxClassifier without an injected session"
                ) from exc
            session = ort.InferenceSession(str(self.model_path), providers=list(config.providers))
        self.metadata = load_model_metadata(config.metadata_path, verify_hash=False) if config.metadata_path else None
        self.labels = self.metadata.class_names if self.metadata and self.metadata.class_names else config.labels

        self.session = session
        self.input_name = _io_name(session.get_inputs(), "input")
        self.output_names = [_io_name([output], f"output_{idx}") for idx, output in enumerate(session.get_outputs())]

    def classify(self, crop: np.ndarray) -> Classification:
        if crop.ndim not in {2, 3}:
            raise ValueError("crop must be HxW or HxWxC")
        tensor = _preprocess_crop(crop, self.config.input_width, self.config.input_height)
        outputs = self.session.run(self.output_names, {self.input_name: tensor})
        logits = np.asarray(outputs[0], dtype=np.float32)
        if logits.ndim == 2 and logits.shape[0] == 1:
            logits = logits[0]
        if logits.ndim != 1:
            raise RuntimeError(f"unsupported classifier output shape: {logits.shape}")
        probs = _softmax(logits)
        class_id = int(np.argmax(probs))
        label = self.labels[class_id] if class_id < len(self.labels) else "Unknown"
        confidence = float(probs[class_id])
        is_civilian = label in set(self.config.civilian_labels)
        return Classification(label, confidence, is_civilian)


def _io_name(items: Sequence[Any], fallback: str) -> str:
    if not items:
        return fallback
    return str(getattr(items[0], "name", fallback))


def _preprocess_crop(crop: np.ndarray, width: int, height: int) -> np.ndarray:
    if crop.ndim == 2:
        crop = np.repeat(crop[:, :, None], 3, axis=2)
    if crop.shape[2] == 1:
        crop = np.repeat(crop, 3, axis=2)
    if crop.shape[2] > 3:
        crop = crop[:, :, :3]
    try:
        import cv2  # type: ignore

        resized = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LINEAR)
    except Exception:
        y_idx = np.linspace(0, crop.shape[0] - 1, height).astype(np.int64)
        x_idx = np.linspace(0, crop.shape[1] - 1, width).astype(np.int64)
        resized = crop[y_idx][:, x_idx]
    tensor = resized.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor)


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    total = np.sum(exp)
    if total <= 0:
        return np.zeros_like(values)
    return exp / total
