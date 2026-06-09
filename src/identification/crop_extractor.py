# crop helpers for the classifier (layer 3).
# expand the bbox to a centred square, pad with zeros if it falls off the
# edge, then resize to out_size. keeps aspect ratio.
from __future__ import annotations

from typing import Any

from src.types import RawDetection


def extract_crop(image: Any, bbox_px: tuple[int, int, int, int], out_size: int = 224) -> Any:
    import cv2
    import numpy as np

    if image is None or getattr(image, "size", 0) == 0:
        raise ValueError("empty image")
    h, w = image.shape[:2]
    x, y, bw, bh = bbox_px
    if bw <= 0 or bh <= 0:
        raise ValueError(f"invalid bbox: {bbox_px}")

    # smallest enclosing square, centred on the bbox
    side = max(bw, bh)
    cx, cy = x + bw / 2.0, y + bh / 2.0
    x1 = int(round(cx - side / 2.0))
    y1 = int(round(cy - side / 2.0))
    x2, y2 = x1 + side, y1 + side

    # clamp then pad whatever fell off the edge
    cx1, cy1 = max(0, x1), max(0, y1)
    cx2, cy2 = min(w, x2), min(h, y2)
    crop = image[cy1:cy2, cx1:cx2]
    pt = cy1 - y1
    pb = y2 - cy2
    pl = cx1 - x1
    pr = x2 - cx2
    if any(p > 0 for p in (pt, pb, pl, pr)):
        crop = np.pad(
            crop,
            ((max(0, pt), max(0, pb)),
             (max(0, pl), max(0, pr)),
             (0, 0)),
            mode="constant", constant_values=0,
        )
    if crop.size == 0:
        # detection completely off-frame - black square
        return np.zeros((out_size, out_size, 3), dtype=np.uint8)
    return cv2.resize(crop, (out_size, out_size), interpolation=cv2.INTER_LINEAR)


def batch_extract(image: Any, detections: list[RawDetection], out_size: int = 224) -> list[Any]:
    return [extract_crop(image, d.bbox_px, out_size) for d in detections]
