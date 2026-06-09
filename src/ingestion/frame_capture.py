# layer 1 - frame capture.
# wraps cv2.VideoCapture, yields BGR frames with monotonic frame_id +
# wall-clock UTC timestamp. threading + shared-memory publish lives one
# level up in src.pipeline so this stays unit-testable on its own.
from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass
class CapturedFrame:
    frame_id: int
    timestamp_utc: str
    image: Any                  # np.ndarray (H, W, 3) uint8 BGR
    capture_latency_ms: float


class FrameCapture:
    # tolerates up to max_failures_in_a_row consecutive read failures before
    # giving up. matches docs/02 §3 (layer-1 fallback: 3 retries -> empty packet).
    def __init__(
        self,
        source: str | int,
        *,
        max_failures_in_a_row: int = 3,
        backend: int | None = None,   # cv2.CAP_FFMPEG / CAP_V4L2 / CAP_GSTREAMER
    ) -> None:
        self.source = source
        self.max_failures = max_failures_in_a_row
        self._backend = backend
        self._cap: Any = None
        self._frame_id = -1

    # ---- lifecycle ----
    def open(self) -> None:
        import cv2  # local import - cheap module load
        if self._backend is not None:
            self._cap = cv2.VideoCapture(self.source, self._backend)
        else:
            self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {self.source!r}")

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self) -> FrameCapture:
        self.open()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ---- iter ----
    def __iter__(self) -> Iterator[CapturedFrame]:
        if self._cap is None:
            self.open()
        fails = 0
        while True:
            t0 = time.perf_counter()
            ok, frame = self._cap.read()
            if not ok or frame is None:
                fails += 1
                if fails >= self.max_failures:
                    return        # source exhausted / unrecoverable
                continue
            fails = 0
            self._frame_id += 1
            yield CapturedFrame(
                frame_id=self._frame_id,
                timestamp_utc=_utc_iso_now(),
                image=frame,
                capture_latency_ms=(time.perf_counter() - t0) * 1000.0,
            )


def _utc_iso_now() -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
