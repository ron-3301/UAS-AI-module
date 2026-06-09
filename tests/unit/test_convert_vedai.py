# smoke + correctness tests for scripts/convert_vedai.py.
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import convert_vedai  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None, reason="Pillow not installed"
)


def _write_img(path: Path, w: int = 512, h: int = 512) -> None:
    from PIL import Image
    Image.new("RGB", (w, h), color=(80, 80, 80)).save(path)


def _vedai_line(class_id: int, xs: list[float], ys: list[float], frame_id: int = 0) -> str:
    # 14-col layout: id cx cy orient x1 x2 x3 x4 y1 y2 y3 y4 class is_contained
    return " ".join(
        [str(frame_id), "0", "0", "0"]
        + [f"{v:.1f}" for v in xs] + [f"{v:.1f}" for v in ys]
        + [str(class_id), "0"]
    )


def test_vedai_end_to_end(tmp_path: Path) -> None:
    ann = tmp_path / "Annotations"
    ann.mkdir()
    imgs = tmp_path / "Images"
    imgs.mkdir()
    dst = tmp_path / "out"
    for i in range(4):
        stem = f"{i:08d}"
        _write_img(imgs / f"{stem}_co.png", 512, 512)
        lines = [
            # car (class 1) -> Vehicle-Wheeled
            _vedai_line(1, [100, 160, 160, 100], [200, 200, 260, 260], i),
            # plane (class 32) -> Aircraft-Fixed
            _vedai_line(32, [300, 360, 360, 300], [300, 300, 360, 360], i),
            # class 10 ("other") -> dropped (unmapped)
            _vedai_line(10, [10, 20, 20, 10], [10, 10, 20, 20], i),
            # class 99 (unknown) -> dropped (unmapped)
            _vedai_line(99, [10, 20, 20, 10], [10, 10, 20, 20], i),
            # tiny box (< 5px) -> dropped
            _vedai_line(1, [50, 53, 53, 50], [50, 50, 53, 53], i),
        ]
        (ann / f"{stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    stats = convert_vedai.convert(ann, imgs, dst, val_fraction=0.25, test_fraction=0.25)
    assert stats["images_out"] == 4
    assert stats["boxes_out"] == 8                # 2 valid per image × 4 images
    assert stats["boxes_dropped"] >= 3 * 4        # 3 invalid per image dropped

    # data.yaml correctness
    data_yaml = (dst / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 7" in data_yaml
    assert "Vehicle-Wheeled" in data_yaml

    # Spot-check a label file
    label_dirs = [dst / "labels" / s for s in ("train", "val", "test")]
    any_label = next((p for d in label_dirs if d.exists() for p in d.iterdir()), None)
    assert any_label is not None
    lines = any_label.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    cls_ids = sorted(int(line.split()[0]) for line in lines)
    assert cls_ids == [1, 4]  # Vehicle-Wheeled + Aircraft-Fixed


def test_vedai_cli_help() -> None:
    # argparse should SystemExit when required args are missing.
    with patch.object(sys, "argv", ["convert_vedai.py"]), pytest.raises(SystemExit):
        convert_vedai.main()
