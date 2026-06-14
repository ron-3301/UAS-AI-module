from __future__ import annotations

# --- OLD CODE FROM SRC ---
from typing import Optional
import numpy as np
class FrameCapture:
    def __init__(self, source: str = "mock"):
        self.source = source; self.frame_id = 0
    def read(self) -> Optional[np.ndarray]:
        if self.source == "mock":
            self.frame_id += 1
            return np.zeros((480, 640, 3), dtype=np.uint8)
        raise NotImplementedError("Real camera not implemented")
# --- END OLD CODE ---

"""Frame capture abstractions.

The real camera backends can be added behind the `FrameSource` protocol. The
mock backend is intentionally deterministic so tests and dry-runs are reliable.
"""


from typing import Protocol

from models import Frame, utc_now


class FrameSource(Protocol):
    """Interface implemented by camera/video sources."""

    def read(self) -> Frame:
        """Return one frame or raise a backend-specific exception."""


class MockFrameSource:
    """Deterministic frame source used for tests and `--dry-run`."""

    def __init__(self, width: int = 640, height: int = 480) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("mock frame dimensions must be positive")
        self.width = width
        self.height = height
        self._counter = 0

    def read(self) -> Frame:
        self._counter += 1
        # Tiny placeholder payload instead of allocating full images in tests.
        payload = f"mock-frame-{self._counter}".encode("utf-8")
        return Frame(
            frame_id=f"mock-{self._counter:06d}",
            timestamp_utc=utc_now(),
            width=self.width,
            height=self.height,
            data=payload,
        )
