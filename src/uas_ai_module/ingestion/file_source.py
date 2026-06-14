"""File-based frame ingestion for local replay and integration testing."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from uas_ai_module.models import Frame


class FileFrameSourceError(ValueError):
    """Raised when a frame file cannot be loaded safely."""


class ImageFileFrameSource:
    """Read one or more image files as pipeline frames.

    Supported without optional dependencies:
    - `.npy` files containing HxW or HxWxC arrays

    Supported when OpenCV is available:
    - common image extensions such as `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`
    """

    def __init__(self, paths: list[str | Path], *, loop: bool = False) -> None:
        if not paths:
            raise FileFrameSourceError("at least one image path is required")
        self.paths = tuple(Path(path) for path in paths)
        self.loop = loop
        self._index = -1

    def read(self) -> Frame:
        next_index = self._index + 1
        if next_index >= len(self.paths):
            if not self.loop:
                raise EOFError("image file source exhausted")
            next_index = 0
        self._index = next_index
        path = self.paths[self._index]
        image = load_image_array(path)
        height, width = image.shape[:2]
        return Frame(
            frame_id=path.stem,
            timestamp_utc=datetime.now(timezone.utc),
            width=int(width),
            height=int(height),
            data=image,
        )


class VideoFileFrameSource:
    """Read frames from a local video file using OpenCV."""

    def __init__(self, path: str | Path, *, loop: bool = False) -> None:
        self.path = Path(path)
        self.loop = loop
        if not self.path.exists():
            raise FileFrameSourceError(f"video file not found: {self.path}")
        try:
            import cv2  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise FileFrameSourceError("OpenCV is required for VideoFileFrameSource") from exc
        self._cv2 = cv2
        self._capture = cv2.VideoCapture(str(self.path))
        if not self._capture.isOpened():
            raise FileFrameSourceError(f"failed to open video file: {self.path}")
        self._counter = 0

    def read(self) -> Frame:
        ok, image = self._capture.read()
        if not ok:
            if not self.loop:
                raise EOFError("video file source exhausted")
            self._capture.set(self._cv2.CAP_PROP_POS_FRAMES, 0)
            ok, image = self._capture.read()
            if not ok:
                raise EOFError("video file source exhausted after loop reset")
        self._counter += 1
        height, width = image.shape[:2]
        return Frame(
            frame_id=f"{self.path.stem}-{self._counter:06d}",
            timestamp_utc=datetime.now(timezone.utc),
            width=int(width),
            height=int(height),
            data=image,
        )


def load_image_array(path: str | Path) -> np.ndarray:
    image_path = Path(path)
    if not image_path.exists():
        raise FileFrameSourceError(f"image file not found: {image_path}")
    suffix = image_path.suffix.lower()
    if suffix == ".npy":
        image = np.load(image_path)
    else:
        try:
            import cv2  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise FileFrameSourceError("OpenCV is required for non-.npy image files") from exc
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise FileFrameSourceError(f"failed to read image file: {image_path}")
    if not isinstance(image, np.ndarray):
        raise FileFrameSourceError("loaded image is not a NumPy array")
    if image.ndim not in {2, 3}:
        raise FileFrameSourceError("loaded image must be HxW or HxWxC")
    if image.dtype != np.uint8:
        image = np.clip(image, 0, 255).astype(np.uint8)
    if image.ndim == 2:
        image = image[:, :, None]
    return image
