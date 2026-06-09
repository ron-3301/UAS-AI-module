#!/usr/bin/env python3
# xView -> YOLO, mapped onto our 7-class taxonomy (docs/11).
#
# xView ships as one GeoJSON ('xView_train.geojson') with one feature per
# object. relevant fields:
#   properties.image_id        -> '1234.tif'
#   properties.type_id         -> integer xView class id
#   properties.bounds_imcoords -> "xmin,ymin,xmax,ymax" in pixel coords
# (see https://challenge.xviewdataset.org/data-format)
#
# xView has ~60 leaf classes - we map the operationally relevant ones and
# drop the rest. Person isn't in xView (it's satellite); comes from
# internal annotation (Phase 2 W4).
#
# Mapping is in XVIEW_MAP below. comments group by output class.
#
# usage:
#   python scripts/convert_xview.py \
#       --geojson data/raw/xView/xView_train.geojson \
#       --imgs    data/raw/xView/train_images \
#       --dst     data/processed/v0.3_xview
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

XVIEW_MAP: dict[int, int] = {
    # -> Aircraft-Fixed (4)
    11: 4, 12: 4, 13: 4,
    # -> Aircraft-Rotary (3)
    15: 3,
    # -> Vehicle-Wheeled (1)
    17: 1, 18: 1, 19: 1, 20: 1, 21: 1, 23: 1, 24: 1, 25: 1, 27: 1, 28: 1,
    32: 1, 52: 1, 55: 1, 57: 1, 59: 1, 60: 1,
    # -> Vehicle-Tracked (2)
    53: 2, 54: 2, 56: 2,
    # -> Structure-Temp (6)
    71: 6, 72: 6,
    # -> Watercraft (5)
    50: 5, 93: 5, 94: 5,
}

OUR_CLASS_NAMES = [
    "Person", "Vehicle-Wheeled", "Vehicle-Tracked",
    "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp",
]


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


def _parse_bounds(s: str) -> tuple[float, float, float, float] | None:
    try:
        vals = [float(x) for x in s.split(",")]
        if len(vals) != 4:
            return None
        xmin, ymin, xmax, ymax = vals
        if xmax <= xmin or ymax <= ymin:
            return None
        return xmin, ymin, xmax, ymax
    except ValueError:
        return None


def convert(
    geojson_path: Path,
    imgs_dir: Path,
    dst_root: Path,
    *,
    val_fraction: float = 0.15,
    test_fraction: float = 0.05,
    seed: int = 1337,
) -> dict[str, int]:
    if not _try_pillow():
        raise RuntimeError("Pillow is required (pip install pillow)")
    if not geojson_path.exists():
        raise FileNotFoundError(geojson_path)
    if not imgs_dir.is_dir():
        raise FileNotFoundError(imgs_dir)

    # bucket features by image_id
    with open(geojson_path, encoding="utf-8") as f:
        gj = json.load(f)
    per_image: dict[str, list[tuple[int, tuple[float, float, float, float]]]] = defaultdict(list)

    n_feat = n_mapped = n_dropped = 0
    for feat in gj.get("features", []):
        n_feat += 1
        props = feat.get("properties", {})
        img_id = props.get("image_id")
        type_id = props.get("type_id")
        bounds = props.get("bounds_imcoords")
        if not (img_id and isinstance(type_id, int) and bounds):
            n_dropped += 1
            continue
        bb = _parse_bounds(bounds)
        if bb is None:
            n_dropped += 1
            continue
        mapped = XVIEW_MAP.get(type_id)
        if mapped is None:
            n_dropped += 1
            continue
        per_image[img_id].append((mapped, bb))
        n_mapped += 1

    # deterministic split by image id
    image_ids = sorted(per_image)
    rng = random.Random(seed)
    rng.shuffle(image_ids)
    n = len(image_ids)
    n_val  = int(n * val_fraction)
    n_test = int(n * test_fraction)
    split_of = {iid: "val"   for iid in image_ids[:n_val]}
    split_of.update({iid: "test"  for iid in image_ids[n_val:n_val + n_test]})
    split_of.update({iid: "train" for iid in image_ids[n_val + n_test:]})

    for s in ("train", "val", "test"):
        (dst_root / "images" / s).mkdir(parents=True, exist_ok=True)
        (dst_root / "labels" / s).mkdir(parents=True, exist_ok=True)

    n_img_out = n_box_out = n_tiny = 0
    for img_id, boxes in per_image.items():
        src_img = imgs_dir / img_id
        if not src_img.exists():
            continue
        try:
            iw, ih = _image_size(src_img)
        except Exception as e:
            print(f"  ! unreadable image {src_img}: {e}", file=sys.stderr)
            continue

        out_lines: list[str] = []
        for our_cls, (xmin, ymin, xmax, ymax) in boxes:
            # clamp + sanity
            xmin = max(0.0, xmin)
            ymin = max(0.0, ymin)
            xmax = min(float(iw), xmax)
            ymax = min(float(ih), ymax)
            w = xmax - xmin
            h = ymax - ymin
            if w < 5 or h < 5:
                n_tiny += 1
                continue
            cx = (xmin + w / 2) / iw
            cy = (ymin + h / 2) / ih
            out_lines.append(f"{our_cls} {cx:.6f} {cy:.6f} {w / iw:.6f} {h / ih:.6f}")
            n_box_out += 1

        if not out_lines:
            continue
        split = split_of[img_id]
        shutil.copy2(src_img, dst_root / "images" / split / src_img.name)
        (dst_root / "labels" / split / f"{src_img.stem}.txt").write_text(
            "\n".join(out_lines) + "\n", encoding="utf-8"
        )
        n_img_out += 1

    _write_data_yaml(dst_root)
    return {
        "features_total":   n_feat,
        "features_mapped":  n_mapped,
        "features_dropped": n_dropped,
        "images_out":       n_img_out,
        "boxes_out":        n_box_out,
        "boxes_tiny":       n_tiny,
    }


def _write_data_yaml(dst_root: Path) -> Path:
    lines = [
        "# Auto-generated by scripts/convert_xview.py",
        f"path: {dst_root.resolve()}",
        "train: images/train",
        "val:   images/val",
        "test:  images/test",
        "",
        f"nc: {len(OUR_CLASS_NAMES)}",
        "names:",
    ]
    for i, name in enumerate(OUR_CLASS_NAMES):
        lines.append(f"  {i}: {name}")
    out = dst_root / "data.yaml"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geojson", type=Path, required=True)
    ap.add_argument("--imgs",    type=Path, required=True)
    ap.add_argument("--dst",     type=Path, required=True)
    ap.add_argument("--val-fraction",  type=float, default=0.15)
    ap.add_argument("--test-fraction", type=float, default=0.05)
    ap.add_argument("--seed",    type=int, default=1337)
    args = ap.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    stats = convert(
        args.geojson, args.imgs, args.dst,
        val_fraction=args.val_fraction, test_fraction=args.test_fraction, seed=args.seed,
    )
    print("xView conversion complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())