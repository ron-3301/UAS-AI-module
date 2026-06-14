from __future__ import annotations

"""TensorRT detector boundary.

A full TensorRT implementation requires Jetson/TensorRT runtime libraries that
are not available in this workspace. This class validates `.engine` artifacts and
provides a clear error until the hardware backend is implemented.
"""


from pathlib import Path

from detection.detector import RuntimeModelConfigError, validate_runtime_model_path
from models import Detection, Frame


class TensorRtDetector:
    """Validated TensorRT detector placeholder for Jetson bring-up."""

    def __init__(self, engine_path: str | Path) -> None:
        self.engine_path = validate_runtime_model_path(engine_path)
        if self.engine_path.suffix.lower() != ".engine":
            raise RuntimeModelConfigError("TensorRtDetector requires a .engine artifact")

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        _ = frame
        raise RuntimeError(
            "TensorRT detector backend is not implemented in this rebuild environment; "
            f"validated engine path is {self.engine_path}"
        )
