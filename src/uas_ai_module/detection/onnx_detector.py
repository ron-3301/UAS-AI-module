"""ONNX Runtime detector wrapper.

The wrapper is intentionally lightweight and dependency-optional: importing this
module does not require `onnxruntime`; constructing an `OnnxDetector` without an
injected session does. This keeps tests and non-Jetson development environments
usable while preserving a clear runtime boundary.

Supported output layouts for the MVP:

1. `(N, 6)` or `(1, N, 6)` as `[x1, y1, x2, y2, confidence, class_id]`.
2. `(N, 5 + C)` or `(1, N, 5 + C)` as `[cx, cy, w, h, objectness, class_scores...]`.

Coordinates may be normalized `[0, 1]`, in model-input pixels, or already in
frame pixels. They are clipped to frame bounds before NMS.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from uas_ai_module.detection.detector import RuntimeModelConfigError, validate_runtime_model_path
from uas_ai_module.detection.nms import BoxCandidate, clip_xyxy, nms
from uas_ai_module.model_metadata import ModelMetadataError, load_model_metadata
from uas_ai_module.models import Detection, Frame

DEFAULT_CLASS_NAMES = (
    "Person",
    "Vehicle-Wheeled",
    "Vehicle-Tracked",
    "Aircraft-Rotary",
    "Aircraft-Fixed",
    "Watercraft",
    "Structure-Temp",
)


@dataclass(frozen=True)
class OnnxDetectorConfig:
    model_path: str | Path
    input_width: int = 640
    input_height: int = 640
    conf_threshold: float = 0.30
    iou_threshold: float = 0.45
    max_detections: int = 300
    class_names: tuple[str, ...] = DEFAULT_CLASS_NAMES
    providers: tuple[str, ...] = ("CUDAExecutionProvider", "CPUExecutionProvider")
    metadata_path: str | Path | None = None

    def validate(self) -> None:
        model_path = validate_runtime_model_path(self.model_path)
        if model_path.suffix.lower() != ".onnx":
            raise RuntimeModelConfigError("OnnxDetector requires a .onnx model artifact")
        if self.input_width <= 0 or self.input_height <= 0:
            raise RuntimeModelConfigError("ONNX detector input dimensions must be positive")
        if not 0.0 <= self.conf_threshold <= 1.0:
            raise RuntimeModelConfigError("conf_threshold must be in [0, 1]")
        if not 0.0 <= self.iou_threshold <= 1.0:
            raise RuntimeModelConfigError("iou_threshold must be in [0, 1]")
        if self.max_detections <= 0:
            raise RuntimeModelConfigError("max_detections must be positive")
        if not self.class_names:
            raise RuntimeModelConfigError("class_names must not be empty")
        if self.metadata_path is not None:
            try:
                metadata = load_model_metadata(self.metadata_path, verify_hash=False)
            except ModelMetadataError as exc:
                raise RuntimeModelConfigError(str(exc)) from exc
            if metadata.role != "detector":
                raise RuntimeModelConfigError("detector metadata role must be 'detector'")
            if metadata.backend != "onnxruntime":
                raise RuntimeModelConfigError("ONNX detector metadata backend must be 'onnxruntime'")
            if Path(metadata.artifact).name != Path(model_path).name:
                raise RuntimeModelConfigError("detector metadata artifact does not match model_path")
            if len(metadata.input_shape) >= 4:
                if metadata.input_shape[-2] != self.input_height or metadata.input_shape[-1] != self.input_width:
                    raise RuntimeModelConfigError("detector metadata input shape does not match configured input size")


class OnnxDetector:
    """Detector backed by ONNX Runtime or an ONNX Runtime-compatible session."""

    def __init__(self, config: OnnxDetectorConfig, *, session: Any | None = None) -> None:
        config.validate()
        self.config = config
        self.model_path = validate_runtime_model_path(config.model_path)

        if session is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"ONNX detector model not found: {self.model_path}")
            try:
                import onnxruntime as ort  # type: ignore
            except Exception as exc:  # pragma: no cover - environment-dependent
                raise RuntimeError(
                    "onnxruntime is required to construct OnnxDetector without an injected session"
                ) from exc
            session = ort.InferenceSession(str(self.model_path), providers=list(config.providers))

        self.metadata = load_model_metadata(config.metadata_path, verify_hash=False) if config.metadata_path else None
        self.class_names = self.metadata.class_names if self.metadata and self.metadata.class_names else config.class_names

        self.session = session
        self.input_name = self._first_io_name(session.get_inputs(), "input")
        self.output_names = [
            self._single_io_name(output, f"output_{idx}")
            for idx, output in enumerate(session.get_outputs())
        ]

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        image = _frame_to_numpy(frame)
        input_tensor = _preprocess(image, self.config.input_width, self.config.input_height)
        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
        candidates = self._decode_outputs(outputs, frame_width=frame.width, frame_height=frame.height)
        kept = nms(
            candidates,
            iou_threshold=self.config.iou_threshold,
            class_agnostic=False,
            max_detections=self.config.max_detections,
        )
        detections = tuple(self._candidate_to_detection(candidate) for candidate in kept)
        for detection in detections:
            detection.validate()
        return detections

    def _decode_outputs(
        self, outputs: Sequence[Any], *, frame_width: int, frame_height: int
    ) -> tuple[BoxCandidate, ...]:
        if not outputs:
            return ()
        raw = np.asarray(outputs[0], dtype=np.float32)
        if raw.ndim == 3 and raw.shape[0] == 1:
            raw = raw[0]
        if raw.ndim != 2:
            raise RuntimeError(f"unsupported ONNX detector output shape: {raw.shape}")
        if raw.shape[1] < 6:
            raise RuntimeError(f"detector output must have at least 6 columns, got {raw.shape}")

        if raw.shape[1] == 6:
            return self._decode_xyxy_conf_class(raw, frame_width=frame_width, frame_height=frame_height)
        return self._decode_cxcywh_obj_classes(raw, frame_width=frame_width, frame_height=frame_height)

    def _decode_xyxy_conf_class(
        self, raw: np.ndarray, *, frame_width: int, frame_height: int
    ) -> tuple[BoxCandidate, ...]:
        candidates: list[BoxCandidate] = []
        for row in raw:
            score = float(row[4])
            if score < self.config.conf_threshold:
                continue
            class_id = int(round(float(row[5])))
            x1, y1, x2, y2 = _scale_xyxy(
                row[:4],
                frame_width=frame_width,
                frame_height=frame_height,
                input_width=self.config.input_width,
                input_height=self.config.input_height,
            )
            candidates.append(BoxCandidate(x1, y1, x2, y2, score, class_id))
        return tuple(candidates)

    def _decode_cxcywh_obj_classes(
        self, raw: np.ndarray, *, frame_width: int, frame_height: int
    ) -> tuple[BoxCandidate, ...]:
        candidates: list[BoxCandidate] = []
        for row in raw:
            objectness = float(row[4])
            class_scores = row[5:]
            if class_scores.size == 0:
                continue
            class_id = int(np.argmax(class_scores))
            score = objectness * float(class_scores[class_id])
            if score < self.config.conf_threshold:
                continue
            cx, cy, w, h = map(float, row[:4])
            x1 = cx - w / 2.0
            y1 = cy - h / 2.0
            x2 = cx + w / 2.0
            y2 = cy + h / 2.0
            x1, y1, x2, y2 = _scale_xyxy(
                (x1, y1, x2, y2),
                frame_width=frame_width,
                frame_height=frame_height,
                input_width=self.config.input_width,
                input_height=self.config.input_height,
            )
            candidates.append(BoxCandidate(x1, y1, x2, y2, score, class_id))
        return tuple(candidates)

    def _candidate_to_detection(self, candidate: BoxCandidate) -> Detection:
        class_label = _class_name(candidate.class_id, self.class_names)
        return Detection(
            class_label=class_label,
            confidence=float(candidate.score),
            bbox_xyxy=candidate.bbox,
            track_id=None,
            sublabel=None,
            id_confidence=None,
            is_civilian=None,
            source="onnx",
        )

    @staticmethod
    def _io_name(items: Sequence[Any], fallback: str) -> str:
        if not items:
            return fallback
        return str(getattr(items[0], "name", fallback))

    @staticmethod
    def _single_io_name(item: Any, fallback: str) -> str:
        return str(getattr(item, "name", fallback))

    @classmethod
    def _first_io_name(cls, items: Sequence[Any], fallback: str) -> str:
        return cls._io_name(items, fallback)


def _frame_to_numpy(frame: Frame) -> np.ndarray:
    image = frame.data
    if not isinstance(image, np.ndarray):
        raise ValueError("OnnxDetector requires Frame.data to be a NumPy array")
    if image.ndim not in {2, 3}:
        raise ValueError("Frame.data must be HxW or HxWxC")
    if image.shape[0] != frame.height or image.shape[1] != frame.width:
        raise ValueError("Frame dimensions do not match NumPy image shape")
    return image


def _preprocess(image: np.ndarray, input_width: int, input_height: int) -> np.ndarray:
    if image.ndim == 2:
        image = np.repeat(image[:, :, None], 3, axis=2)
    if image.shape[2] == 1:
        image = np.repeat(image, 3, axis=2)
    if image.shape[2] > 3:
        image = image[:, :, :3]

    resized = _resize(image, input_width, input_height)
    tensor = resized.astype(np.float32) / 255.0
    tensor = np.transpose(tensor, (2, 0, 1))[None, :, :, :]
    return np.ascontiguousarray(tensor)


def _resize(image: np.ndarray, width: int, height: int) -> np.ndarray:
    try:
        import cv2  # type: ignore

        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
    except Exception:
        # Fallback nearest-neighbour resize for test/minimal environments.
        y_idx = np.linspace(0, image.shape[0] - 1, height).astype(np.int64)
        x_idx = np.linspace(0, image.shape[1] - 1, width).astype(np.int64)
        return image[y_idx][:, x_idx]


def _scale_xyxy(
    xyxy: Iterable[float],
    *,
    frame_width: int,
    frame_height: int,
    input_width: int,
    input_height: int,
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = map(float, xyxy)
    max_coord = max(abs(x1), abs(y1), abs(x2), abs(y2))
    if max_coord <= 1.5:
        scaled = (x1 * frame_width, y1 * frame_height, x2 * frame_width, y2 * frame_height)
    elif max_coord <= max(input_width, input_height) * 1.5:
        scaled = (
            x1 * frame_width / input_width,
            y1 * frame_height / input_height,
            x2 * frame_width / input_width,
            y2 * frame_height / input_height,
        )
    else:
        scaled = (x1, y1, x2, y2)
    return clip_xyxy(scaled, width=frame_width, height=frame_height)


def _class_name(class_id: int, class_names: Sequence[str]) -> str:
    if 0 <= class_id < len(class_names):
        return class_names[class_id]
    return "Unknown"
