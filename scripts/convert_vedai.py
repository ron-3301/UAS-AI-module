#!/usr/bin/env python3
# VEDAI -> YOLO, mapped onto our 7-class taxonomy (docs/11).
#
# VEDAI ships at two resolutions (512 and 1024). Per-frame annotations live
# in `<frame_id>.txt` files. Each line layout (per VEDAI docs):
#
#   id  cx  cy  orient  x1 x2 x3 x4  y1 y2 y3 y4  class  is_contained [is_occluded]
#
# coords are pixels in the matching image, class is VEDAI class id, orient
# is rotation in radians.
#
# VEDAI id -> our class:
#    1 car          -> Vehicle-Wheeled
#    2 truck        -> Vehicle-Wheeled
#    4 tractor      -> Vehicle-Wheeled
#    5 camping car  -> Vehicle-Wheeled
#    7 motorcycle   -> Vehicle-Wheeled
#    8 bus          -> Vehicle-Wheeled
#    9 van          -> Vehicle-Wheeled
#   10 other        -> dropped
#   11 small        -> dropped (ambiguous)
#   23 pickup       -> Vehicle-Wheeled
#   31 ship/boat    -> Watercraft
#   32 plane        -> Aircraft-Fixed
#
# tracked vehicles, helicopters, persons, temp structures are NOT in VEDAI -
# those come from xView + internal annotation (Phase 2 W4).
#
# usage:
#   python scripts/convert_vedai.py \
#       --src  data/raw/VEDAI/Annotations1024 \
#       --imgs data/raw/VEDAI/Vehicules1024 \
#       --dst  data/processed/v0.2_vedai \
#       --val-fraction 0.15
from __future__ import annotations

import argparse
import random
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path

# VEDAI id -> (our_class_id, our_name)
VEDAI_MAP: dict[int, tuple[int, str]] = {
    1:  (1, "Vehicle-Wheeled"),    # car
    2:  (1, "Vehicle-Wheeled"),    # truck
    4:  (1, "Vehicle-Wheeled"),    # tractor (wheeled in VEDAI)
    5:  (1, "Vehicle-Wheeled"),    # camping car
    7:  (1, "Vehicle-Wheeled"),    # motorcycle
    8:  (1, "Vehicle-Wheeled"),    # bus
    9:  (1, "Vehicle-Wheeled"),    # van
    23: (1, "Vehicle-Wheeled"),    # pickup
    31: (5, "Watercraft"),         # boat / ship
    32: (4, "Aircraft-Fixed"),     # plane
}

OUR_CLASS_NAMES = [
    "Person", "Vehicle-Wheeled", "Vehicle-Tracked",
    "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp",
]

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff")


def _try_pillow() -> bool:
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def _image_size(p: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(p) as im:
        return im.size


def _find_image(imgs_dir: Path, stem: str) -> Path | None:
    # VEDAI uses <stem>_co.png for the colour image and <stem>_ir.png for IR.
    # prefer colour.
    for ext in IMAGE_EXTS:
        for name in (f"{stem}_co{ext}", f"{stem}.png", f"{stem}{ext}"):
            p = imgs_dir / name
            if p.exists():
                return p
    return None


def _parse_vedai_line(line: str) -> tuple[int, tuple[float, float, float, float], int] | None:
    # returns (frame_id_unused, axis_aligned_xywh_px, vedai_class) or None.
    # handles 14- and 15-col layouts.
    parts = line.strip().split()
    if len(parts) < 14:
        return None
    try:
        # field 0 = frame id (unused)
        # fields 4..7 = x1..x4 ; fields 8..11 = y1..y4 ; field 12 = class
        xs = [float(parts[i]) for i in (4, 5, 6, 7)]
        ys = [float(parts[i]) for i in (8, 9, 10, 11)]
        cls = int(parts[12])
    except (ValueError, IndexError):
        return None
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    w = xmax - xmin
    h = ymax - ymin
    if w <= 0 or h <= 0:
        return None
    return 0, (xmin, ymin, w, h), cls


def convert(
    ann_dir: Path,
    imgs_dir: Path,
    dst_root: Path,
    *,
    val_fraction: float = 0.15,
    test_fraction: float = 0.05,
    seed: int = 1337,
) -> dict[str, int]:
    if not _try_pillow():
        raise RuntimeError("Pillow is required (pip install pillow)")
    if not ann_dir.is_dir():
        raise FileNotFoundError(f"Annotation dir not found: {ann_dir}")
    if not imgs_dir.is_dir():
        raise FileNotFoundError(f"Image dir not found: {imgs_dir}")

    stems: list[str] = sorted(p.stem for p in ann_dir.glob("*.txt"))
    rng = random.Random(seed)
    rng.shuffle(stems)

    n = len(stems)
    n_val  = int(n * val_fraction)
    n_test = int(n * test_fraction)
    splits = {
        "val":   set(stems[:n_val]),
        "test":  set(stems[n_val : n_val + n_test]),
        "train": set(stems[n_val + n_test :]),
    }

    for s in ("train", "val", "test"):
        (dst_root / "images" / s).mkdir(parents=True, exist_ok=True)
        (dst_root / "labels" / s).mkdir(parents=True, exist_ok=True)

    n_img_out = n_box_out = n_box_dropped = 0
    for stem in stems:
        split = next(s for s, members in splits.items() if stem in members)
        img_src = _find_image(imgs_dir, stem)
        if img_src is None:
            continue
        try:
            iw, ih = _image_size(img_src)
        except Exception as e:
            print(f"  ! unreadable image {img_src}: {e}", file=sys.stderr)
            continue

        out_lines: list[str] = []
        for raw in (ann_dir / f"{stem}.txt").read_text(encoding="utf-8").splitlines():
            parsed = _parse_vedai_line(raw)
            if parsed is None:
                continue
            _, (x, y, w, h), vedai_cls = parsed
            mapped = VEDAI_MAP.get(vedai_cls)
            if mapped is None:
                n_box_dropped += 1
                continue
            our_cls, _ = mapped
            # clamp to image bounds
            x = max(0.0, x)
            y = max(0.0, y)
            w = min(w, iw - x)
            h = min(h, ih - y)
            if w < 5 or h < 5:
                n_box_dropped += 1
                continue
            cx = (x + w / 2) / iw
            cy = (y + h / 2) / ih
            out_lines.append(
                f"{our_cls} {cx:.6f} {cy:.6f} {w / iw:.6f} {h / ih:.6f}"
            )
            n_box_out += 1

        if not out_lines:
            continue
        shutil.copy2(img_src, dst_root / "images" / split / img_src.name)
        (dst_root / "labels" / split / f"{img_src.stem}.txt").write_text(
            "\n".join(out_lines) + "\n", encoding="utf-8"
        )
        n_img_out += 1

    _write_data_yaml(dst_root, ["train", "val", "test"])
    return {
        "annotations_seen": n,
        "images_out":       n_img_out,
        "boxes_out":        n_box_out,
        "boxes_dropped":    n_box_dropped,
    }


def _write_data_yaml(dst_root: Path, splits: Iterable[str]) -> Path:
    lines = [
        "# Auto-generated by scripts/convert_vedai.py",
        f"path: {dst_root.resolve()}",
        "train: images/train",
        "val:   images/val",
    ]
    if "test" in list(splits):
        lines.append("test:  images/test")
    lines.append("")
    lines.append(f"nc: {len(OUR_CLASS_NAMES)}")
    lines.append("names:")
    for i, name in enumerate(OUR_CLASS_NAMES):
        lines.append(f"  {i}: {name}")
    out = dst_root / "data.yaml"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src",  type=Path, required=True, help="VEDAI annotations dir")
    ap.add_argument("--imgs", type=Path, required=True, help="VEDAI images dir (same resolution as --src)")
    ap.add_argument("--dst",  type=Path, required=True, help="output dataset root (versioned)")
    ap.add_argument("--val-fraction",  type=float, default=0.15)
    ap.add_argument("--test-fraction", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    stats = convert(
        args.src, args.imgs, args.dst,
        val_fraction=args.val_fraction, test_fraction=args.test_fraction, seed=args.seed,
    )
    print("VEDAI conversion complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())