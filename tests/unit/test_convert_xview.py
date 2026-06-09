# tests for scripts/convert_xview.py.
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import convert_xview  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None, reason="Pillow not installed"
)


def _img(path: Path, w: int = 1024, h: int = 1024) -> None:
    from PIL import Image
    Image.new("RGB", (w, h), color=(100, 100, 100)).save(path)


def test_xview_end_to_end(tmp_path: Path) -> None:
    imgs_dir = tmp_path / "imgs"
    imgs_dir.mkdir()
    dst = tmp_path / "out"
    features = []
    for i in range(4):
        name = f"img_{i}.tif"
        _img(imgs_dir / name, 1024, 1024)
        features.extend([
            # 17 -> Vehicle-Wheeled (cls 1): 100x60 box at (200,300)
            {"type": "Feature", "properties": {
                "image_id": name, "type_id": 17, "bounds_imcoords": "200,300,300,360",
            }},
            # 15 -> Aircraft-Rotary (cls 3): 200x150 box at (400,500)
            {"type": "Feature", "properties": {
                "image_id": name, "type_id": 15, "bounds_imcoords": "400,500,600,650",
            }},
            # 99 unmapped -> dropped
            {"type": "Feature", "properties": {
                "image_id": name, "type_id": 99, "bounds_imcoords": "10,10,20,20",
            }},
            # tiny -> dropped
            {"type": "Feature", "properties": {
                "image_id": name, "type_id": 17, "bounds_imcoords": "0,0,3,3",
            }},
            # malformed bounds -> dropped
            {"type": "Feature", "properties": {
                "image_id": name, "type_id": 17, "bounds_imcoords": "bad,bad",
            }},
        ])
    gj = {"type": "FeatureCollection", "features": features}
    geo_path = tmp_path / "x.geojson"
    geo_path.write_text(json.dumps(gj), encoding="utf-8")

    stats = convert_xview.convert(
        geo_path, imgs_dir, dst, val_fraction=0.25, test_fraction=0.25,
    )
    assert stats["images_out"] == 4
    # 2 valid boxes per image -> 8 total. 1 tiny per image -> 4 total.
    # 1 unmapped + 1 malformed per image -> 8 features dropped.
    assert stats["boxes_out"] == 8
    assert stats["boxes_tiny"] == 4
    assert stats["features_dropped"] >= 8

    # data.yaml correctness
    assert "nc: 7" in (dst / "data.yaml").read_text(encoding="utf-8")

    # Spot-check a label file: classes 1 and 3, normalised coords
    label_dirs = [dst / "labels" / s for s in ("train", "val", "test")]
    labels = [p for d in label_dirs if d.exists() for p in d.iterdir()]
    assert labels
    lines = labels[0].read_text(encoding="utf-8").strip().splitlines()
    cls_ids = sorted(int(line.split()[0]) for line in lines)
    assert cls_ids == [1, 3]
    for line in lines:
        parts = line.split()
        for v in parts[1:]:
            assert 0.0 < float(v) < 1.0


def test_xview_drops_missing_image(tmp_path: Path) -> None:
    imgs_dir = tmp_path / "imgs"
    imgs_dir.mkdir()
    dst = tmp_path / "out"
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {
            "image_id": "ghost.tif", "type_id": 17, "bounds_imcoords": "10,10,200,200",
        }},
    ]}
    geo_path = tmp_path / "x.geojson"
    geo_path.write_text(json.dumps(gj), encoding="utf-8")
    stats = convert_xview.convert(geo_path, imgs_dir, dst)
    assert stats["images_out"] == 0
    assert stats["boxes_out"] == 0
