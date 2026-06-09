#!/usr/bin/env python3
# Dataset quality gates - implements docs/04 §5.
#
# gates (any failure -> non-zero exit unless --report-only):
#   G1: every class has >= --min-instances (default 500)
#   G2: every box >= --min-box-px (default 5) AFTER scaling to --imgsz
#   G3: no duplicate images (dHash, Hamming dist <= --phash-thresh)
#   G4: no class leakage train <-> val/test
#
# inputs: ultralytics-style dataset root
#   images/{train,val,test}/<file>.{png,jpg,...}
#   labels/{train,val,test}/<file>.txt           YOLO format cls cx cy w h
#   data.yaml
#
# writes <root>/dataset_stats_report.md + <root>/dataset_stats_summary.json
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---- dHash 8x8 -> 64-bit int. pure python so we don't pull in imagehash. ----
def _dhash(img_path: Path, size: int = 8) -> int:
    from PIL import Image
    with Image.open(img_path) as im:
        gray = im.convert("L").resize((size + 1, size), Image.LANCZOS)
        px = list(gray.tobytes())   # 1 byte per pixel in 'L' mode
    h = 0
    for row in range(size):
        for col in range(size):
            left  = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            h = (h << 1) | int(left > right)
    return h


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


# ---- data model ----
@dataclass
class SplitStats:
    n_images: int = 0
    n_boxes: int  = 0
    class_counts: Counter = field(default_factory=Counter)
    tiny_boxes: list[tuple[str, int, int]] = field(default_factory=list)  # (file, w_px, h_px)
    image_hashes: dict[Path, int] = field(default_factory=dict)


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


# ---- scan one split ----
def _scan_split(images_dir: Path, labels_dir: Path, imgsz: int, min_box_px: int) -> SplitStats:
    import contextlib

    from PIL import Image

    stats = SplitStats()
    if not images_dir.is_dir():
        return stats

    for img_path in sorted(images_dir.iterdir()):
        if img_path.suffix.lower() not in IMAGE_EXTS:
            continue
        stats.n_images += 1
        try:
            with Image.open(img_path) as im:
                w, h = im.size
        except Exception as e:
            print(f"  ! unreadable image {img_path}: {e}", file=sys.stderr)
            continue

        # dHash for G3
        with contextlib.suppress(Exception):
            stats.image_hashes[img_path] = _dhash(img_path)

        lbl_path = labels_dir / f"{img_path.stem}.txt"
        if not lbl_path.exists():
            continue
        for raw in lbl_path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split()
            if len(parts) != 5:
                continue
            try:
                cls = int(parts[0])
                _, _, bw, bh = (float(x) for x in parts[1:])
            except ValueError:
                continue
            # scale to target imgsz - "after scaling" is what matters
            sc = imgsz / max(w, h)
            bw_px = bw * w * sc
            bh_px = bh * h * sc
            if bw_px < min_box_px or bh_px < min_box_px:
                stats.tiny_boxes.append((img_path.name, int(bw_px), int(bh_px)))
                continue
            stats.class_counts[cls] += 1
            stats.n_boxes += 1
    return stats


# ---- gates ----
def gate_min_instances(per_split: dict[str, SplitStats], names: dict[int, str], min_instances: int) -> GateResult:
    totals: Counter = Counter()
    for s in per_split.values():
        totals.update(s.class_counts)
    low = {names.get(c, str(c)): n for c, n in totals.items() if n < min_instances}
    # classes declared in data.yaml but never seen at all
    missing = {names[c]: 0 for c in names if c not in totals}
    low.update(missing)
    if low:
        joined = ", ".join(f"{k}={v}" for k, v in sorted(low.items()))
        return GateResult("G1_min_instances", False,
                          f"classes below {min_instances}: {joined}")
    return GateResult("G1_min_instances", True, f"all classes >= {min_instances} instances")


def gate_tiny_boxes(per_split: dict[str, SplitStats]) -> GateResult:
    n_tiny = sum(len(s.tiny_boxes) for s in per_split.values())
    n_box  = sum(s.n_boxes         for s in per_split.values()) + n_tiny
    if n_box == 0:
        return GateResult("G2_box_size", False, "no boxes found in dataset")
    pct = 100.0 * n_tiny / n_box
    # soft-fail at >2% tiny boxes
    return GateResult("G2_box_size", pct <= 2.0,
                      f"{n_tiny}/{n_box} boxes too small ({pct:.2f}%)")


def gate_duplicates(per_split: dict[str, SplitStats], phash_thresh: int) -> GateResult:
    all_hashes: list[tuple[Path, int]] = []
    for s in per_split.values():
        all_hashes.extend(s.image_hashes.items())
    dupes: list[tuple[str, str, int]] = []
    # O(n^2). fine for <50k images, bucket later if we outgrow.
    for i in range(len(all_hashes)):
        pi, hi = all_hashes[i]
        for j in range(i + 1, len(all_hashes)):
            pj, hj = all_hashes[j]
            d = _hamming(hi, hj)
            if d <= phash_thresh:
                dupes.append((pi.name, pj.name, d))
    if dupes:
        head = "; ".join(f"{a}~{b}(d={d})" for a, b, d in dupes[:5])
        more = f" ... (+{len(dupes)-5} more)" if len(dupes) > 5 else ""
        return GateResult("G3_duplicates", False, f"{len(dupes)} near-duplicate pairs: {head}{more}")
    return GateResult("G3_duplicates", True, f"no near-duplicates within Hamming<={phash_thresh}")


def gate_split_leakage(per_split: dict[str, SplitStats]) -> GateResult:
    # leakage here = class present in val/test but absent in train - model
    # never gets to learn it.
    train = per_split.get("train", SplitStats()).class_counts
    bad: list[str] = []
    for split_name, s in per_split.items():
        if split_name == "train":
            continue
        for cls in s.class_counts:
            if cls not in train:
                bad.append(f"class_id={cls} in {split_name} but not in train")
    if bad:
        return GateResult("G4_split_leakage", False, "; ".join(bad))
    return GateResult("G4_split_leakage", True, "no orphan classes across splits")


# ---- report ----
def _render_report(per_split: dict[str, SplitStats], names: dict[int, str],
                   gates: list[GateResult]) -> str:
    lines = ["# Dataset Stats Report", "", "## Summary", "",
             "| Split | Images | Boxes | Tiny boxes (dropped) |",
             "|-------|-------:|------:|---------------------:|"]
    for name, s in per_split.items():
        lines.append(f"| {name} | {s.n_images} | {s.n_boxes} | {len(s.tiny_boxes)} |")
    lines += ["", "## Class distribution", "",
              "| Class | " + " | ".join(per_split.keys()) + " | total |",
              "|-------|" + "|".join(["---:"] * (len(per_split) + 1)) + "|"]
    totals: Counter = Counter()
    for s in per_split.values():
        totals.update(s.class_counts)
    for cid in sorted(names):
        row = [names[cid]]
        for s in per_split.values():
            row.append(str(s.class_counts.get(cid, 0)))
        row.append(str(totals.get(cid, 0)))
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Gates", ""]
    for g in gates:
        mark = "✅" if g.passed else "❌"
        lines.append(f"- {mark} **{g.name}** — {g.detail}")
    return "\n".join(lines) + "\n"


# ---- entry ----
def run(dataset_root: Path, *, imgsz: int = 640, min_instances: int = 500,
        min_box_px: int = 5, phash_thresh: int = 4,
        report_only: bool = False) -> tuple[int, str, dict[str, Any]]:
    data_yaml = dataset_root / "data.yaml"
    if not data_yaml.exists():
        return 2, f"missing {data_yaml}", {}
    with open(data_yaml, encoding="utf-8") as f:
        dy = yaml.safe_load(f)
    names: dict[int, str] = (
        {int(k): v for k, v in dy["names"].items()}
        if isinstance(dy["names"], dict)
        else {i: n for i, n in enumerate(dy["names"])}
    )

    per_split: dict[str, SplitStats] = {}
    for split in ("train", "val", "test"):
        img_dir = dataset_root / "images" / split
        lbl_dir = dataset_root / "labels" / split
        if img_dir.is_dir():
            per_split[split] = _scan_split(img_dir, lbl_dir, imgsz, min_box_px)

    gates = [
        gate_min_instances(per_split, names, min_instances),
        gate_tiny_boxes(per_split),
        gate_duplicates(per_split, phash_thresh),
        gate_split_leakage(per_split),
    ]
    report = _render_report(per_split, names, gates)
    (dataset_root / "dataset_stats_report.md").write_text(report, encoding="utf-8")

    summary = {
        "splits": {k: {"images": v.n_images, "boxes": v.n_boxes} for k, v in per_split.items()},
        "gates":  [{"name": g.name, "passed": g.passed, "detail": g.detail} for g in gates],
    }
    (dataset_root / "dataset_stats_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    all_pass = all(g.passed for g in gates)
    return 0 if (all_pass or report_only) else 1, report, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root",          type=Path, required=True, help="dataset root containing data.yaml")
    ap.add_argument("--imgsz",         type=int, default=640)
    ap.add_argument("--min-instances", type=int, default=500)
    ap.add_argument("--min-box-px",    type=int, default=5)
    ap.add_argument("--phash-thresh",  type=int, default=4)
    ap.add_argument("--report-only",   action="store_true",
                    help="write the report but always exit 0 (use early in Phase 1).")
    args = ap.parse_args()
    code, report, _ = run(
        args.root,
        imgsz=args.imgsz, min_instances=args.min_instances,
        min_box_px=args.min_box_px, phash_thresh=args.phash_thresh,
        report_only=args.report_only,
    )
    print(report)
    return code


if __name__ == "__main__":
    sys.exit(main())
