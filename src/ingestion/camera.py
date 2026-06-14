from __future__ import annotations

"""Camera ingestion backends.

The OpenCV source is read-only and fail-fast. Tests can inject a fake capture
object, so importing this module does not require camera hardware.
"""


from datetime import datetime, timezone
from typing import Any

import numpy as np

from models import Frame


class CameraSourceError(RuntimeError):
    """Raised when a camera frame cannot be captured safely."""


class OpenCvCameraSource:
    """Read frames from an OpenCV `VideoCapture` source."""

    def __init__(self, source: int | str = 0, *, capture: Any | None = None, camera_id: str = "cam") -> None:
        self.source = source
        self.camera_id = camera_id
        self._capture = capture
        self._counter = 0
        if self._capture is None:
            try:
                import cv2  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise CameraSourceError("OpenCV is required for OpenCvCameraSource") from exc
            self._capture = cv2.VideoCapture(source)
        if hasattr(self._capture, "isOpened") and not self._capture.isOpened():
            raise CameraSourceError(f"camera source is not open: {source}")

    def read(self) -> Frame:
        ok, image = self._capture.read()
        if not ok or image is None:
            raise CameraSourceError("failed to read frame from camera source")
        if not isinstance(image, np.ndarray):
            raise CameraSourceError("camera returned non-NumPy frame")
        if image.ndim not in {2, 3}:
            raise CameraSourceError("camera frame must be HxW or HxWxC")
        self._counter += 1
        height, width = image.shape[:2]
        return Frame(
            frame_id=f"{self.camera_id}-{self._counter:06d}",
            timestamp_utc=datetime.now(timezone.utc),
            width=int(width),
            height=int(height),
            data=image,
        )

    def release(self) -> None:
        if hasattr(self._capture, "release"):
            self._capture.release()
