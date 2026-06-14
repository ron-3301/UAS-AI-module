"""Frame capture abstractions.

The real camera backends can be added behind the `FrameSource` protocol. The
mock backend is intentionally deterministic so tests and dry-runs are reliable.
"""
from __future__ import annotations

from typing import Protocol

from uas_ai_module.models import Frame, utc_now


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
