# tests for the framecapture wrapper using a tiny synthetic video file.
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("cv2") is None or importlib.util.find_spec("numpy") is None,
    reason="opencv-python or numpy not installed",
)


def _make_video(path: Path, n_frames: int = 5, w: int = 64, h: int = 48, fps: int = 10) -> Path:
    import cv2
    import numpy as np
    # mp4v works in OpenCV builds without ffmpeg, and produces a tiny file.
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    assert writer.isOpened(), "VideoWriter failed to open"
    for i in range(n_frames):
        frame = np.full((h, w, 3), 30 * (i % 8), dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def test_frame_capture_yields_all_frames(tmp_path: Path) -> None:
    from src.ingestion.frame_capture import FrameCapture
    video = _make_video(tmp_path / "tiny.mp4", n_frames=5)
    captured = []
    with FrameCapture(str(video)) as cap:
        for frame in cap:
            captured.append(frame)
    assert len(captured) >= 3, f"only got {len(captured)} frames"
    # Monotonically increasing frame_id starting at 0
    fids = [f.frame_id for f in captured]
    assert fids == list(range(len(captured)))
    # Capture latency is recorded
    assert all(f.capture_latency_ms >= 0 for f in captured)
    # Images are non-empty BGR
    assert all(f.image.shape == (48, 64, 3) for f in captured)


def test_frame_capture_raises_on_bad_source(tmp_path: Path) -> None:
    from src.ingestion.frame_capture import FrameCapture
    with pytest.raises(RuntimeError, match="Failed to open"):
        FrameCapture(str(tmp_path / "does_not_exist.mp4")).open()


def test_utc_iso_now_format() -> None:
    from src.ingestion.frame_capture import _utc_iso_now
    s = _utc_iso_now()
    assert s.endswith("Z") and "T" in s
