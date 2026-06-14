from __future__ import annotations

# --- OLD CODE FROM SRC ---
from typing import List, Dict, Any
import numpy as np
def extract_crops(frame: np.ndarray, detections: List[Dict]) -> List[np.ndarray]:
    crops = []
    for det in detections:
        x, y, w, h = det["bbox"]
        crop = frame[y:y+h, x:x+w]
        if crop.size > 0: crops.append(crop)
    return crops
# --- END OLD CODE ---

"""Crop extraction for detection classification."""


import numpy as np

from detection.nms import clip_xyxy
from models import Detection, Frame


class CropExtractionError(ValueError):
    """Raised when a detection crop cannot be extracted safely."""


def extract_crop(frame: Frame, detection: Detection, *, padding_px: int = 0) -> np.ndarray:
    """Extract a clipped crop from `Frame.data` for a detection.

    The function is intentionally strict about image shape so classification does
    not proceed on ambiguous or non-image frame payloads.
    """

    if not isinstance(frame.data, np.ndarray):
        raise CropExtractionError("frame data is not a NumPy image")
    image = frame.data
    if image.ndim not in {2, 3}:
        raise CropExtractionError("frame image must be HxW or HxWxC")
    if image.shape[0] != frame.height or image.shape[1] != frame.width:
        raise CropExtractionError("frame metadata dimensions do not match image shape")
    if padding_px < 0:
        raise CropExtractionError("padding_px must be non-negative")

    x1, y1, x2, y2 = detection.bbox_xyxy
    padded = (x1 - padding_px, y1 - padding_px, x2 + padding_px, y2 + padding_px)
    x1c, y1c, x2c, y2c = clip_xyxy(padded, width=frame.width, height=frame.height)
    x1i, y1i, x2i, y2i = map(lambda value: int(round(value)), (x1c, y1c, x2c, y2c))
    if x2i <= x1i or y2i <= y1i:
        raise CropExtractionError("detection crop has zero area after clipping")
    return image[y1i:y2i, x1i:x2i].copy()
