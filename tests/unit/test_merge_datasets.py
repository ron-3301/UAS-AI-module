# tests for scripts/merge_datasets.py — the w5 deliverable.
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import merge_datasets as md  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None, reason="Pillow not installed"
)

OUR = md.OUR_CLASS_NAMES


def _mk_source(root: Path, source_name: str, *,
                images: list[tuple[str, list[tuple[int, float, float, float, float]]]]) -> Path:
    """Build a minimal YOLO source dataset on disk."""
    from PIL import Image
    src = root / source_name
    for split in ("train",):
        (src / "images" / split).mkdir(parents=True)
        (src / "labels" / split).mkdir(parents=True)
    for i, (name, boxes) in enumerate(images):
        img_name = name if name.endswith(".png") else f"{name}_{i:03d}.png"
        Image.new("RGB", (200, 200), color=(i * 37 % 255, 128, 64)).save(
            src / "images" / "train" / img_name
        )
        (src / "labels" / "train" / f"{Path(img_name).stem}.txt").write_text(
            "\n".join(f"{c} {cx} {cy} {w} {h}" for c, cx, cy, w, h in boxes) + "\n",
            encoding="utf-8",
        )
    # Minimal data.yaml that matches the canonical taxonomy.
    names = "\n".join(f"  {i}: {n}" for i, n in enumerate(OUR))
    (src / "data.yaml").write_text(
        f"path: {src}\ntrain: images/train\nval: images/train\nnc: {len(OUR)}\nnames:\n{names}\n",
        encoding="utf-8",
    )
    return src


def test_merge_two_sources_stratified(tmp_path: Path) -> None:
    big = (0.5, 0.5, 0.4, 0.4)
    src_a = _mk_source(
        tmp_path / "raw", "src_a",
        images=[("a", [(1, *big), (1, *big)])] * 10,  # 10 Vehicle-Wheeled images
    )
    src_b = _mk_source(
        tmp_path / "raw", "src_b",
        images=[("b", [(4, *big)])] * 10,             # 10 Aircraft-Fixed images
    )
    dst = tmp_path / "v1.0"
    summary = md.merge(
        [(src_a, "src_a"), (src_b, "src_b")],
        dst,
        splits=(0.6, 0.2, 0.2),
    )

    total = sum(summary["images_per_split"].values())
    assert total == 20
    # Stratified: every split should contain BOTH source classes.
    for split in ("train", "val", "test"):
        cls_counts: dict[int, int] = {}
        lbl_dir = dst / "labels" / split
        for lbl in lbl_dir.iterdir():
            for line in lbl.read_text(encoding="utf-8").splitlines():
                cls = int(line.split()[0])
                cls_counts[cls] = cls_counts.get(cls, 0) + 1
        assert 1 in cls_counts, f"{split} missing Vehicle-Wheeled: {cls_counts}"
        assert 4 in cls_counts, f"{split} missing Aircraft-Fixed: {cls_counts}"

    # Namespaced filenames — no collision possible.
    train_files = list((dst / "images" / "train").iterdir())
    assert all(f.name.startswith(("src_a__", "src_b__")) for f in train_files), [
        f.name for f in train_files]

    # Manifest CSV is valid
    with open(dst / "manifest.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 20
    assert {"source", "split", "merged_path"} <= set(rows[0])

    # CHANGELOG and data.yaml exist
    assert (dst / "data.yaml").is_file()
    assert (dst / "CHANGELOG.md").is_file()


def test_merge_rejects_incompatible_taxonomy(tmp_path: Path) -> None:
    src = _mk_source(tmp_path / "raw", "src_x", images=[("x", [(0, 0.5, 0.5, 0.3, 0.3)])])
    # Sabotage the data.yaml -> wrong nc.
    (src / "data.yaml").write_text(
        f"path: {src}\ntrain: images/train\nval: images/train\nnc: 3\nnames:\n  0: a\n  1: b\n  2: c\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nc="):
        md.merge([(src, "src_x")], tmp_path / "v1.0")


def test_split_fractions_must_sum_to_one(tmp_path: Path) -> None:
    src = _mk_source(tmp_path / "raw", "src_y",
                      images=[("y", [(0, 0.5, 0.5, 0.3, 0.3)])] * 3)
    with pytest.raises(ValueError, match="sum to 1"):
        md.merge([(src, "src_y")], tmp_path / "v1.0", splits=(0.5, 0.5, 0.5))
