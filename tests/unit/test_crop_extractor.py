# tests for the crop extractor.
from __future__ import annotations

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("cv2") is None or importlib.util.find_spec("numpy") is None,
    reason="opencv-python or numpy not installed",
)


def _make_image(w: int = 200, h: int = 200):
    import numpy as np
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[50:150, 50:150] = 200          # white-ish square in the middle
    return img


def test_extract_centred_crop_correct_shape() -> None:
    from src.identification.crop_extractor import extract_crop
    img = _make_image()
    out = extract_crop(img, (50, 50, 100, 100), out_size=224)
    assert out.shape == (224, 224, 3)


def test_extract_pads_when_offedge() -> None:

    from src.identification.crop_extractor import extract_crop
    img = _make_image()
    # bbox starts before (0,0) – must pad with zeros, not crash
    out = extract_crop(img, (-20, -20, 40, 40), out_size=64)
    assert out.shape == (64, 64, 3)
    # Top-left corner came from off-image padding -> zeros.
    assert int(out[0, 0].sum()) == 0


def test_extract_rejects_invalid_bbox() -> None:

    from src.identification.crop_extractor import extract_crop
    with pytest.raises(ValueError):
        extract_crop(_make_image(), (10, 10, 0, 10))


def test_extract_rejects_empty_image() -> None:
    from src.identification.crop_extractor import extract_crop
    with pytest.raises(ValueError):
        extract_crop(None, (0, 0, 10, 10))


def test_batch_extract() -> None:
    from src.identification.crop_extractor import batch_extract
    from src.types import RawDetection

    img = _make_image()
    dets = [
        RawDetection(bbox_px=(10, 10, 80, 80), detection_class="A", detection_confidence=0.9),
        RawDetection(bbox_px=(100, 100, 80, 80), detection_class="B", detection_confidence=0.8),
    ]
    crops = batch_extract(img, dets, out_size=64)
    assert len(crops) == 2 and all(c.shape == (64, 64, 3) for c in crops)
