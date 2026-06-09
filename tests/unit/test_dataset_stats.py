# tests for the dataset-stats quality gates (docs/04 §5).
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from scripts.dataset_stats import run

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PIL") is None, reason="Pillow not installed"
)


def _mk_dataset(tmp_path: Path, *,
                train_imgs: list[tuple[str, list[tuple[int, float, float, float, float]]]],
                val_imgs:   list[tuple[str, list[tuple[int, float, float, float, float]]]],
                nc: int = 3) -> Path:
    """Build a tiny YOLO dataset on disk. Each entry is (name, [boxes]) where
    each box = (cls, cx, cy, w, h) normalised."""
    import random

    from PIL import Image
    root = tmp_path / "ds"
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True)
        (root / "labels" / split).mkdir(parents=True)

    def _noisy_image(seed: int):
        # Solid colours have a flat dHash — generate per-pixel noise so each
        # image has a distinct perceptual hash unless we explicitly request a
        # duplicate.
        rnd = random.Random(seed)
        im = Image.new("RGB", (64, 64))
        im.putdata([(rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
                    for _ in range(64 * 64)])
        return im.resize((200, 200), Image.NEAREST)

    def _write(split: str, items):
        for i, (name, boxes) in enumerate(items):
            real_name = f"img_{split}_{i:03d}.png" if name in {"AUTO", "DUP"} else name
            # Same seed for DUP entries → identical hash; unique seed otherwise.
            seed = 0 if name == "DUP" else hash((split, i)) & 0xFFFFFFFF
            _noisy_image(seed).save(root / "images" / split / real_name)
            (root / "labels" / split / f"{Path(real_name).stem}.txt").write_text(
                "\n".join(f"{c} {cx} {cy} {w} {h}" for c, cx, cy, w, h in boxes) + "\n",
                encoding="utf-8",
            )

    _write("train", train_imgs)
    _write("val",   val_imgs)

    names_yaml = "\n".join(f"  {i}: cls{i}" for i in range(nc))
    (root / "data.yaml").write_text(
        f"path: {root}\ntrain: images/train\nval: images/val\nnc: {nc}\nnames:\n{names_yaml}\n",
        encoding="utf-8",
    )
    return root


def test_all_gates_pass_on_clean_dataset(tmp_path: Path) -> None:
    # 3 classes, plenty of instances each, no dupes, no class leakage, healthy boxes.
    big_box = (0.5, 0.5, 0.4, 0.4)   # 80x80 px - well above 5px threshold
    train = [("AUTO", [(0, *big_box), (1, *big_box), (2, *big_box)]) for _ in range(4)]
    val   = [("AUTO", [(0, *big_box), (1, *big_box), (2, *big_box)]) for _ in range(2)]
    root = _mk_dataset(tmp_path, train_imgs=train, val_imgs=val, nc=3)
    code, _, summary = run(root, min_instances=2, phash_thresh=2)
    gates = {g["name"]: g["passed"] for g in summary["gates"]}
    assert all(gates.values()), gates
    assert code == 0


def test_min_instances_gate_fires(tmp_path: Path) -> None:
    # class 2 only appears once.
    big = (0.5, 0.5, 0.4, 0.4)
    train = [("AUTO", [(0, *big), (1, *big)]) for _ in range(5)]
    train.append(("AUTO", [(2, *big)]))   # one instance of class 2
    val = [("AUTO", [(0, *big), (1, *big)])]
    root = _mk_dataset(tmp_path, train_imgs=train, val_imgs=val, nc=3)
    code, _, summary = run(root, min_instances=5, phash_thresh=2)
    g = {x["name"]: x for x in summary["gates"]}
    assert g["G1_min_instances"]["passed"] is False
    assert "cls2" in g["G1_min_instances"]["detail"]
    assert code == 1


def test_tiny_boxes_dropped_and_reported(tmp_path: Path) -> None:
    # imgsz=640 (default). On a 200x200 image the scale is 640/200 = 3.2.
    # A normalised box of 0.005 -> 1 px raw -> 3.2 px after scaling: below the 5px gate.
    tiny  = (0.5, 0.5, 0.005, 0.005)
    big   = (0.5, 0.5, 0.4,   0.4)
    train = [("AUTO", [(0, *big), (0, *tiny), (1, *big), (2, *big)]) for _ in range(3)]
    val   = [("AUTO", [(0, *big), (1, *big), (2, *big)])]
    root = _mk_dataset(tmp_path, train_imgs=train, val_imgs=val, nc=3)
    _, _, summary = run(root, min_instances=1, phash_thresh=2)
    assert summary["splits"]["train"]["boxes"] == 9  # 3 imgs * (3 valid), tiny dropped
    assert summary["splits"]["val"]["boxes"]   == 3  # 1 img * 3 valid
    g2 = next(x for x in summary["gates"] if x["name"] == "G2_box_size")
    # 3 tiny / (3 tiny + 9 + 3 valid) = 3/15 = 20%
    assert g2["detail"].startswith("3/15")


def test_split_leakage_detected(tmp_path: Path) -> None:
    big = (0.5, 0.5, 0.4, 0.4)
    train = [("AUTO", [(0, *big), (1, *big)]) for _ in range(3)]
    val   = [("AUTO", [(2, *big)])]   # class 2 never in train!
    root = _mk_dataset(tmp_path, train_imgs=train, val_imgs=val, nc=3)
    _, _, summary = run(root, min_instances=1, phash_thresh=2)
    g4 = next(x for x in summary["gates"] if x["name"] == "G4_split_leakage")
    assert g4["passed"] is False
    assert "class_id=2" in g4["detail"]


def test_report_only_always_zero(tmp_path: Path) -> None:
    # Same broken dataset as above but with --report-only.
    big = (0.5, 0.5, 0.4, 0.4)
    root = _mk_dataset(
        tmp_path,
        train_imgs=[("AUTO", [(0, *big), (1, *big)])],
        val_imgs=[("AUTO", [(2, *big)])],
        nc=3,
    )
    code, _, _ = run(root, min_instances=1, phash_thresh=2, report_only=True)
    assert code == 0
