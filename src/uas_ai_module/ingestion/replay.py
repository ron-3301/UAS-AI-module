"""Deterministic mission replay ingestion.

Replay mode is the first integration harness for the rebuilt runtime. It lets us
exercise the full advisory pipeline from recorded/synthetic frame metadata plus
telemetry without camera, MAVLink, TensorRT, or ONNX hardware dependencies.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from uas_ai_module.models import Frame, Telemetry


class ReplayError(ValueError):
    """Raised when a replay manifest is malformed or exhausted."""


@dataclass(frozen=True)
class ReplayItem:
    frame: Frame
    telemetry: Telemetry


class ReplayDataset:
    """Shared cursor over replay frames and telemetry.

    `ReplayFrameSource.read()` advances the cursor. `ReplayTelemetrySource.read()`
    returns telemetry for the current frame. This matches the pipeline call order:
    read frame first, then telemetry.
    """

    def __init__(self, items: tuple[ReplayItem, ...], *, loop: bool = False, mission_id: str = "replay") -> None:
        if not items:
            raise ReplayError("replay dataset must contain at least one frame")
        self.items = items
        self.loop = loop
        self.mission_id = mission_id
        self._index = -1

    @classmethod
    def from_manifest(cls, path: str | Path) -> "ReplayDataset":
        manifest_path = Path(path)
        data = json.loads(manifest_path.read_text())
        if not isinstance(data, dict):
            raise ReplayError("replay manifest root must be an object")
        frames = data.get("frames")
        if not isinstance(frames, list) or not frames:
            raise ReplayError("replay manifest must contain a non-empty frames list")

        items: list[ReplayItem] = []
        base_dir = manifest_path.parent
        for idx, entry in enumerate(frames):
            if not isinstance(entry, dict):
                raise ReplayError(f"frame entry {idx} must be an object")
            items.append(_parse_replay_item(entry, base_dir=base_dir, index=idx))
        return cls(tuple(items), loop=bool(data.get("loop", False)), mission_id=str(data.get("mission_id", "replay")))

    @property
    def current(self) -> ReplayItem:
        if self._index < 0:
            raise ReplayError("replay cursor has not been advanced; read a frame first")
        return self.items[self._index]

    def next_item(self) -> ReplayItem:
        next_index = self._index + 1
        if next_index >= len(self.items):
            if not self.loop:
                raise EOFError("replay dataset exhausted")
            next_index = 0
        self._index = next_index
        return self.items[self._index]


class ReplayFrameSource:
    """Pipeline frame source backed by a `ReplayDataset`."""

    def __init__(self, dataset: ReplayDataset) -> None:
        self.dataset = dataset

    def read(self) -> Frame:
        return self.dataset.next_item().frame


class ReplayTelemetrySource:
    """Pipeline telemetry source backed by the current `ReplayDataset` item."""

    def __init__(self, dataset: ReplayDataset) -> None:
        self.dataset = dataset

    def read(self) -> Telemetry:
        return self.dataset.current.telemetry


def _parse_replay_item(entry: dict[str, Any], *, base_dir: Path, index: int) -> ReplayItem:
    frame_id = str(entry.get("frame_id", f"replay-{index:06d}"))
    timestamp = _parse_datetime(str(entry["timestamp_utc"]))
    width = int(entry["width"])
    height = int(entry["height"])
    if width <= 0 or height <= 0:
        raise ReplayError(f"frame {frame_id}: width/height must be positive")
    data = _load_or_generate_image(entry, base_dir=base_dir, width=width, height=height)
    frame = Frame(frame_id=frame_id, timestamp_utc=timestamp, width=width, height=height, data=data)

    telemetry_data = entry.get("telemetry")
    if not isinstance(telemetry_data, dict):
        raise ReplayError(f"frame {frame_id}: telemetry must be an object")
    telemetry = _parse_telemetry(telemetry_data, default_timestamp=timestamp)
    return ReplayItem(frame=frame, telemetry=telemetry)


def _load_or_generate_image(entry: dict[str, Any], *, base_dir: Path, width: int, height: int) -> np.ndarray:
    image_path = entry.get("image_path")
    if image_path:
        return _load_image(base_dir / str(image_path), width=width, height=height)

    fill_value = entry.get("fill_value", 0)
    if isinstance(fill_value, list):
        if len(fill_value) != 3:
            raise ReplayError("fill_value list must contain exactly three channel values")
        pixel = np.asarray(fill_value, dtype=np.uint8)
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[:, :] = pixel
        return image
    return np.full((height, width, 3), int(fill_value), dtype=np.uint8)


def _load_image(path: Path, *, width: int, height: int) -> np.ndarray:
    if not path.exists():
        raise ReplayError(f"replay image not found: {path}")
    try:
        import cv2  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ReplayError("OpenCV is required to load image_path replay entries") from exc
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ReplayError(f"failed to read replay image: {path}")
    if image.shape[0] != height or image.shape[1] != width:
        raise ReplayError(
            f"replay image shape {image.shape[1]}x{image.shape[0]} does not match manifest {width}x{height}"
        )
    return image


def _parse_telemetry(data: dict[str, Any], *, default_timestamp: datetime) -> Telemetry:
    return Telemetry(
        timestamp_utc=_parse_datetime(str(data.get("timestamp_utc", default_timestamp.isoformat()))),
        lat_deg=float(data["lat_deg"]),
        lon_deg=float(data["lon_deg"]),
        alt_msl_m=float(data["alt_msl_m"]),
        alt_agl_m=float(data["alt_agl_m"]) if data.get("alt_agl_m") is not None else None,
        roll_deg=float(data.get("roll_deg", 0.0)),
        pitch_deg=float(data.get("pitch_deg", 0.0)),
        yaw_deg=float(data.get("yaw_deg", 0.0)),
        velocity_ned_mps=tuple(float(x) for x in data.get("velocity_ned_mps", (0.0, 0.0, 0.0))),
    )


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
