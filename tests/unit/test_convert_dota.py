# smoke + correctness test for scripts/convert_dota.py.
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
CONVERTER = REPO / "scripts" / "convert_dota.py"

# Import the module directly so that line coverage is recorded.
sys.path.insert(0, str(REPO))
from scripts import convert_dota  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None,
    reason="Pillow not installed",
)


def _write_dota_image(path: Path, w: int = 200, h: int = 200) -> None:
    from PIL import Image
    Image.new("RGB", (w, h), color=(50, 100, 150)).save(path)


def _write_dota_label(path: Path, rows: list[tuple[list[float], str]]) -> None:
    lines = ["imagesource:GoogleEarth", "gsd:0.5"]
    for coords, name in rows:
        # DOTA format: x1 y1 x2 y2 x3 y3 x4 y4 name difficulty
        lines.append(" ".join(f"{c:.1f}" for c in coords) + f" {name} 0")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_converter_end_to_end(tmp_path: Path) -> None:
    src = tmp_path / "DOTA"
    dst = tmp_path / "processed" / "v0.1_dota_baseline"
    for split in ("train", "val"):
        (src / split / "images").mkdir(parents=True)
        (src / split / "labelTxt").mkdir(parents=True)

    # --- train: a plane (axis-aligned 60x40 box at (50,50)) and a junk class ---
    _write_dota_image(src / "train" / "images" / "img001.png", 200, 200)
    _write_dota_label(
        src / "train" / "labelTxt" / "img001.txt",
        [
            ([50, 50, 110, 50, 110, 90, 50, 90], "plane"),         # -> Aircraft-Fixed (4)
            ([10, 10, 12, 10, 12, 12, 10, 12], "small-vehicle"),   # degenerate -> filtered
            ([0, 0, 10, 0, 10, 10, 0, 10], "tennis-court"),        # not in our taxonomy
        ],
    )
    # --- val: a ship ---
    _write_dota_image(src / "val" / "images" / "img002.png", 200, 200)
    _write_dota_label(
        src / "val" / "labelTxt" / "img002.txt",
        [([20, 20, 100, 20, 100, 60, 20, 60], "ship")],            # -> Watercraft (5)
    )

    # Call main() in-process so coverage tracks the lines, then also run as a
    # subprocess once with --help to exercise the argparse plumbing.
    argv = ["convert_dota.py",
            "--src", str(src), "--dst", str(dst),
            "--splits", "train", "val"]
    with patch.object(sys, "argv", argv):
        rc = convert_dota.main()
    assert rc == 0
    help_run = subprocess.run(
        [sys.executable, str(CONVERTER), "--help"],
        capture_output=True, text=True, check=False,
    )
    assert help_run.returncode == 0

    # ---- data.yaml ----
    data_yaml = (dst / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 7" in data_yaml
    assert "Aircraft-Fixed" in data_yaml and "Vehicle-Tracked" in data_yaml

    # ---- train label ----
    train_lbl = (dst / "labels" / "train" / "img001.txt").read_text(encoding="utf-8").strip().splitlines()
    # Only the "plane" survives (junk class dropped, tiny box dropped).
    assert len(train_lbl) == 1
    cls_id, cx, cy, w, h = train_lbl[0].split()
    assert int(cls_id) == 4                # Aircraft-Fixed
    # 60-wide, 40-tall box at (50,50) in a 200x200 image:
    # cx=(50+30)/200=0.4   cy=(50+20)/200=0.35   w=60/200=0.3   h=40/200=0.2
    assert float(cx) == pytest.approx(0.4,  abs=1e-3)
    assert float(cy) == pytest.approx(0.35, abs=1e-3)
    assert float(w)  == pytest.approx(0.3,  abs=1e-3)
    assert float(h)  == pytest.approx(0.2,  abs=1e-3)

    # ---- val label ----
    val_lbl = (dst / "labels" / "val" / "img002.txt").read_text(encoding="utf-8").strip().splitlines()
    assert len(val_lbl) == 1
    assert val_lbl[0].split()[0] == "5"    # Watercraft

    # ---- 'current' symlink wired up ----
    current = dst.parent / "current"
    assert current.is_symlink() and current.resolve() == dst.resolve()
