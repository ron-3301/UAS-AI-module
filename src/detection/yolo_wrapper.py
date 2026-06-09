# detector wrapper. two implementations behind one interface:
#   UltralyticsDetector - loads .pt/.onnx/.engine via ultralytics. prod.
#   MockDetector        - scripted, used in tests + replay path so we can
#                         exercise the full pipeline without weights.
# both expose __call__(packet) -> list[RawDetection].
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.types import FramePacket, RawDetection

# 7-class taxonomy. has to stay in sync with scripts/convert_*.py.
CLASS_NAMES: list[str] = [
    'Person', 'Vehicle-Wheeled', 'Vehicle-Tracked',
    'Aircraft-Rotary', 'Aircraft-Fixed', 'Watercraft', 'Structure-Temp',
]


class UltralyticsDetector:
    def __init__(
        self,
        weights: str | Path,
        *,
        conf_threshold: float = 0.45,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
        device: str | int = "cpu",
    ) -> None:
        self.weights = str(weights)
        self.conf = conf_threshold
        self.iou = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self._model: Any | None = None

    def _load(self) -> Any:  # pragma: no cover - needs real weights
        if self._model is None:
            from ultralytics import YOLO  # type: ignore
            self._model = YOLO(self.weights)
        return self._model

    def __call__(self, packet: FramePacket) -> list[RawDetection]:  # pragma: no cover
        m = self._load()
        res = m.predict(
            source=packet.image,
            imgsz=self.imgsz,
            conf=self.conf,
            iou=self.iou,
            device=self.device,
            verbose=False,
        )
        out: list[RawDetection] = []
        if not res:
            return out
        r0 = res[0]
        boxes = getattr(r0, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return out

        # ultralytics gives xyxy in pixel coords
        xyxy = boxes.xyxy.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        cls  = boxes.cls.cpu().numpy().astype(int)
        for i in range(len(xyxy)):
            x1, y1, x2, y2 = (int(round(v)) for v in xyxy[i])
            w, h = x2 - x1, y2 - y1
            if w <= 0 or h <= 0:
                continue
            ci = int(cls[i])
            if ci < 0 or ci >= len(CLASS_NAMES):
                continue
            out.append(RawDetection(
                bbox_px=(x1, y1, w, h),
                detection_class=CLASS_NAMES[ci],
                detection_confidence=float(conf[i]),
            ))
        return out


class MockDetector:
    # deterministic, scripted detector. used in tests + the integration replay path.
    def __init__(self, script: Callable[[FramePacket], list[RawDetection]]) -> None:
        self.script = script

    def __call__(self, packet: FramePacket) -> list[RawDetection]:
        return list(self.script(packet))
