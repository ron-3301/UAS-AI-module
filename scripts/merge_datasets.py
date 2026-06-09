#!/usr/bin/env python3
# Merge multiple per-source YOLO datasets into one versioned dataset.
#
# This is the W5 keystone - produces data/processed/v1.0/ from the per-source
# outputs of convert_dota / convert_vedai / convert_xview / internal / synthetic.
#
# what it does:
#   - verifies every source uses our 7-class taxonomy (nc=7, names match
#     OUR_CLASS_NAMES byte-for-byte). loud fail otherwise.
#   - copies (or symlinks) images into one tree with namespaced filenames
#     "{source}__{stem}.{ext}" so colliding numeric filenames across DOTA /
#     VEDAI / xView don't silently overwrite.
#   - writes a manifest.csv (source / orig path / merged path / split /
#     per-class box counts per image). active-learning loop uses it (doc 4 §2).
#   - stratified re-split (default 80/10/10) at the image level. stratify key
#     is each image's dominant class (most boxes wins).
#   - emits final data.yaml + CHANGELOG.md.
#
# usage:
#   python scripts/merge_datasets.py \
#       --src data/processed/v0.1_dota_baseline:dota \
#             data/processed/v0.2_vedai:vedai \
#             data/processed/v0.3_xview:xview \
#       --dst data/processed/v1.0 \
#       --splits 0.8 0.1 0.1
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

OUR_CLASS_NAMES = [
    "Person", "Vehicle-Wheeled", "Vehicle-Tracked",
    "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp",
]
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


@dataclass
class ImageRecord:
    source: str
    src_img: Path
    src_lbl: Path
    new_stem: str
    class_counts: Counter            # cls_id -> n
    dominant_class: int


# ---- source load + taxonomy verification ----
def _load_source(src_root: Path) -> tuple[dict[int, str], list[ImageRecord]]:
    dy = yaml.safe_load((src_root / "data.yaml").read_text(encoding="utf-8"))
    raw_names = dy["names"]
    names = (
        {int(k): v for k, v in raw_names.items()}
        if isinstance(raw_names, dict)
        else {i: n for i, n in enumerate(raw_names)}
    )

    # taxonomy must match exactly. nc + each class name in order.
    if int(dy.get("nc", -1)) != len(OUR_CLASS_NAMES):
        raise ValueError(
            f"{src_root}/data.yaml has nc={dy.get('nc')}, expected {len(OUR_CLASS_NAMES)}"
        )
    for i, expected in enumerate(OUR_CLASS_NAMES):
        if names.get(i) != expected:
            raise ValueError(
                f"{src_root}/data.yaml class index {i} is {names.get(i)!r}, "
                f"expected {expected!r}"
            )

    records: list[ImageRecord] = []
    for split in ("train", "val", "test"):
        img_dir = src_root / "images" / split
        lbl_dir = src_root / "labels" / split
        if not img_dir.is_dir():
            continue
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in IMAGE_EXTS:
                continue
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            if not lbl_path.exists():
                continue
            counts: Counter = Counter()
            for raw in lbl_path.read_text(encoding="utf-8").splitlines():
                parts = raw.strip().split()
                if len(parts) != 5:
                    continue
                try:
                    counts[int(parts[0])] += 1
                except ValueError:
                    continue
            if not counts:
                continue
            records.append(ImageRecord(
                source=src_root.name,
                src_img=img_path,
                src_lbl=lbl_path,
                new_stem="",   # filled in later by caller (knows the namespace)
                class_counts=counts,
                dominant_class=counts.most_common(1)[0][0],
            ))
    return names, records


# ---- stratified split ----
def _stratified_split(
    records: list[ImageRecord],
    fractions: tuple[float, float, float],
    seed: int,
) -> dict[str, list[ImageRecord]]:
    if abs(sum(fractions) - 1.0) > 1e-6:
        raise ValueError(f"split fractions must sum to 1.0, got {fractions}")
    _f_train, f_val, f_test = fractions
    rng = random.Random(seed)
    by_class: dict[int, list[ImageRecord]] = defaultdict(list)
    for r in records:
        by_class[r.dominant_class].append(r)

    out: dict[str, list[ImageRecord]] = {"train": [], "val": [], "test": []}
    for _cls, items in by_class.items():
        rng.shuffle(items)
        n = len(items)
        # special-case tiny classes - put everything in train rather than starving val/test
        n_val  = max(1, int(n * f_val))  if n >= 3 else 0
        n_test = max(1, int(n * f_test)) if n >= 3 else 0
        out["val"].extend(items[:n_val])
        out["test"].extend(items[n_val:n_val + n_test])
        out["train"].extend(items[n_val + n_test:])
    for s in out:
        rng.shuffle(out[s])
    return out


# ---- emit merged dataset ----
def _emit(dst_root: Path, splits: dict[str, list[ImageRecord]], use_symlinks: bool) -> dict:
    for s in splits:
        (dst_root / "images" / s).mkdir(parents=True, exist_ok=True)
        (dst_root / "labels" / s).mkdir(parents=True, exist_ok=True)

    per_split_counts: dict[str, Counter] = {s: Counter() for s in splits}
    per_split_n: dict[str, int] = {s: 0 for s in splits}
    manifest_rows: list[dict] = []

    for split, records in splits.items():
        for r in records:
            new_name = f"{r.source}__{r.src_img.name}"
            dst_img = dst_root / "images" / split / new_name
            dst_lbl = dst_root / "labels" / split / f"{Path(new_name).stem}.txt"
            if use_symlinks:
                if dst_img.exists() or dst_img.is_symlink():
                    dst_img.unlink()
                dst_img.symlink_to(r.src_img.resolve())
            else:
                shutil.copy2(r.src_img, dst_img)
            shutil.copy2(r.src_lbl, dst_lbl)
            per_split_counts[split].update(r.class_counts)
            per_split_n[split] += 1
            manifest_rows.append({
                "source": r.source,
                "original_path": str(r.src_img),
                "merged_path": str(dst_img.relative_to(dst_root)),
                "split": split,
                **{f"cls_{i}": r.class_counts.get(i, 0) for i in range(len(OUR_CLASS_NAMES))},
            })

    # data.yaml
    yaml_lines = [
        "# Auto-generated by scripts/merge_datasets.py",
        f"path: {dst_root.resolve()}",
        "train: images/train",
        "val:   images/val",
        "test:  images/test",
        "",
        f"nc: {len(OUR_CLASS_NAMES)}",
        "names:",
    ]
    for i, name in enumerate(OUR_CLASS_NAMES):
        yaml_lines.append(f"  {i}: {name}")
    (dst_root / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    # manifest.csv
    manifest_path = dst_root / "manifest.csv"
    fieldnames = (list(manifest_rows[0].keys()) if manifest_rows
                  else ["source", "original_path", "merged_path", "split"])
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(manifest_rows)

    # CHANGELOG.md
    totals: Counter = Counter()
    for s in splits:
        totals.update(per_split_counts[s])
    cl_lines = [
        f"# {dst_root.name}", "",
        "Built by merge_datasets.py from sources: "
        + ", ".join(sorted({r.source for s in splits for r in splits[s]})),
        "",
        "## Class counts (boxes)", "",
        "| class_id | name | train | val | test | total |",
        "|---------:|------|------:|----:|-----:|------:|",
    ]
    for cid, cname in enumerate(OUR_CLASS_NAMES):
        cl_lines.append(
            f"| {cid} | {cname} "
            f"| {per_split_counts['train'].get(cid, 0)} "
            f"| {per_split_counts['val'].get(cid, 0)} "
            f"| {per_split_counts['test'].get(cid, 0)} "
            f"| {totals.get(cid, 0)} |"
        )
    cl_lines += ["", "## Image counts"]
    for s, n in per_split_n.items():
        cl_lines.append(f"- {s}: {n}")
    (dst_root / "CHANGELOG.md").write_text("\n".join(cl_lines) + "\n", encoding="utf-8")

    return {
        "images_per_split": per_split_n,
        "boxes_per_split":  {s: sum(c.values()) for s, c in per_split_counts.items()},
        "boxes_per_class":  {OUR_CLASS_NAMES[i]: totals.get(i, 0)
                             for i in range(len(OUR_CLASS_NAMES))},
        "manifest":         str(manifest_path),
        "changelog":        str(dst_root / "CHANGELOG.md"),
    }


# ---- public api ----
def merge(
    sources: list[tuple[Path, str]],
    dst_root: Path,
    *,
    splits: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 1337,
    symlink_images: bool = False,
) -> dict:
    all_records: list[ImageRecord] = []
    for src_path, src_name in sources:
        _names, records = _load_source(src_path)
        # use the user-supplied namespace, not the path stem
        for r in records:
            r.source = src_name
        all_records.extend(records)
    if not all_records:
        raise RuntimeError("No usable records found in any source dataset.")
    split_records = _stratified_split(all_records, splits, seed)
    summary = _emit(dst_root, split_records, use_symlinks=symlink_images)

    # repoint `current` symlink to the new version
    current = dst_root.parent / "current"
    try:
        if current.is_symlink() or current.exists():
            if current.is_symlink() or current.is_file():
                current.unlink()
            else:
                shutil.rmtree(current)
        current.symlink_to(dst_root.resolve(), target_is_directory=True)
        summary["current_symlink"] = str(current)
    except OSError as e:  # pragma: no cover - non-fatal
        summary["current_symlink_error"] = str(e)
    return summary


def _parse_source_spec(spec: str) -> tuple[Path, str]:
    if ":" in spec:
        p, name = spec.rsplit(":", 1)
    else:
        p, name = spec, Path(spec).name
    return Path(p), name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", nargs="+", required=True,
                    help="One or more PATH[:NAME] sources to merge")
    ap.add_argument("--dst", type=Path, required=True)
    ap.add_argument("--splits", nargs=3, type=float, default=[0.8, 0.1, 0.1],
                    metavar=("TRAIN", "VAL", "TEST"))
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--symlink", action="store_true",
                    help="symlink images instead of copying (saves disk)")
    args = ap.parse_args()

    sources = [_parse_source_spec(s) for s in args.src]
    summary = merge(
        sources, args.dst,
        splits=tuple(args.splits), seed=args.seed, symlink_images=args.symlink,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
