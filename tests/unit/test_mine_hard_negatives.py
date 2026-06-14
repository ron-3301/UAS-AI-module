# tests for the w9 hard-negative miner.
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import mine_hard_negatives as mhn  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None, reason="Pillow not installed",
)

CLASS_NAMES = [
    "Person", "Vehicle-Wheeled", "Vehicle-Tracked",
    "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp",
]


def _img(p: Path, w: int = 200, h: int = 200) -> None:
    from PIL import Image
    Image.new("RGB", (w, h), color=(128, 64, 32)).save(p)


def _gt_yolo(cls_id: int, cx: float, cy: float, w: float, h: float) -> str:
    return f"{cls_id} {cx} {cy} {w} {h}"


def test_mining_surfaces_fp_and_fn(tmp_path: Path) -> None:
    images = tmp_path / "img"
    images.mkdir()
    labels = tmp_path / "lbl"
    labels.mkdir()
    preds = tmp_path / "pred"
    preds.mkdir()
    out = tmp_path / "out"

    # img_0: classifier hallucinated a Person, GT empty -> false positive
    _img(images / "img_0.png", 200, 200)
    (labels / "img_0.txt").write_text("", encoding="utf-8")
    (preds / "img_0.json").write_text(json.dumps({"detections": [
        {"bbox_px": [10, 10, 30, 30], "detection_class": "Person",
         "detection_confidence": 0.95},
    ]}), encoding="utf-8")

    # img_1: GT has a Vehicle-Wheeled, predictions empty -> false negative
    _img(images / "img_1.png", 200, 200)
    (labels / "img_1.txt").write_text(
        _gt_yolo(1, 0.5, 0.5, 0.3, 0.3) + "\n", encoding="utf-8")
    (preds / "img_1.json").write_text(json.dumps({"detections": []}), encoding="utf-8")

    # img_2: prediction matches ground truth -> NOT mined
    _img(images / "img_2.png", 200, 200)
    (labels / "img_2.txt").write_text(
        _gt_yolo(1, 0.5, 0.5, 0.3, 0.3) + "\n", encoding="utf-8")
    (preds / "img_2.json").write_text(json.dumps({"detections": [
        {"bbox_px": [70, 70, 60, 60], "detection_class": "Vehicle-Wheeled",
         "detection_confidence": 0.92},
    ]}), encoding="utf-8")

    summary = mhn.mine(
        predictions=mhn._load_predictions(preds),
        labels_dir=labels, images_dir=images, out_dir=out,
        max_images=10, filter_class=None, class_names=CLASS_NAMES,
    )
    assert summary["copied"] == 2
    assert summary["false_positives"] == 1
    assert summary["false_negatives"] == 1
    assert (out / "manifest.csv").is_file()
    # img_2 (the clean one) must NOT have been copied.
    assert not (out / "images" / "img_2.png").exists()


def test_filter_class(tmp_path: Path) -> None:
    images = tmp_path / "img"
    images.mkdir()
    labels = tmp_path / "lbl"
    labels.mkdir()
    preds = tmp_path / "pred"
    preds.mkdir()
    out = tmp_path / "out"

    _img(images / "img_a.png", 200, 200)
    (labels / "img_a.txt").write_text("", encoding="utf-8")
    (preds / "img_a.json").write_text(json.dumps({"detections": [
        {"bbox_px": [10, 10, 30, 30], "detection_class": "Person",
         "detection_confidence": 0.95},
        {"bbox_px": [50, 50, 30, 30], "detection_class": "Watercraft",
         "detection_confidence": 0.95},
    ]}), encoding="utf-8")
    summary = mhn.mine(
        predictions=mhn._load_predictions(preds),
        labels_dir=labels, images_dir=images, out_dir=out,
        max_images=10, filter_class="Person", class_names=CLASS_NAMES,
    )
    # Only the Person false-positive should have surfaced (Watercraft filtered out).
    assert summary["false_positives"] == 1
