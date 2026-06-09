#!/usr/bin/env python3
# W9 - hard-negative miner.
#
# reads a dir of inference logs (one JSON-per-frame, as emitted by
# InMemoryEmitter or saved by sqlite_logger) and surfaces images where the
# detector either:
#   - fired with conf > 0.5 but max IoU vs GT < 0.3 (false positive), or
#   - missed a GT box entirely (false negative).
#
# output is a dir of image copies + YOLO label files (GT, as a starting
# point for the annotator). flow described in docs/04 §2.
#
# usage:
#   python scripts/mine_hard_negatives.py \
#       --predictions  runs/eval/predictions/ \
#       --ground-truth data/processed/v1.0/labels/val/ \
#       --images       data/processed/v1.0/images/val/ \
#       --out          data/annotations/active_learning_batch_001/ \
#       --max-images   500 \
#       --filter-class Person
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from src.detection.nms import _iou


def _load_predictions(pred_dir: Path) -> dict[str, list[dict[str, Any]]]:
    # returns {image_stem: [det_dict, ...]}. each det has bbox_px (x,y,w,h),
    # detection_class, detection_confidence at minimum.
    out: dict[str, list[dict[str, Any]]] = {}
    for jf in sorted(pred_dir.glob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        out[jf.stem] = list(data.get("detections", []))
    return out


def _load_yolo_labels(label_path: Path, img_w: int, img_h: int,
                      class_names: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not label_path.exists():
        return out
    for raw in label_path.read_text(encoding="utf-8").splitlines():
        parts = raw.strip().split()
        if len(parts) != 5:
            continue
        cls = int(parts[0])
        cx, cy, w, h = (float(x) for x in parts[1:])
        x_px = int(round((cx - w / 2) * img_w))
        y_px = int(round((cy - h / 2) * img_h))
        w_px = int(round(w * img_w))
        h_px = int(round(h * img_h))
        if cls < 0 or cls >= len(class_names):
            continue
        out.append({"detection_class": class_names[cls],
                    "bbox_px": (x_px, y_px, w_px, h_px)})
    return out


def _image_size(p: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(p) as im:
        return im.size


def mine(*, predictions: dict[str, list[dict[str, Any]]],
         labels_dir: Path, images_dir: Path,
         out_dir: Path, max_images: int, filter_class: str | None,
         class_names: list[str],
         iou_threshold: float = 0.3,
         fp_conf_threshold: float = 0.5) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)
    (out_dir / "labels").mkdir(exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    counter: Counter = Counter()
    n_copied = 0

    for stem, preds in predictions.items():
        if n_copied >= max_images:
            break

        # locate the image (any common extension)
        img_path = None
        for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            p = images_dir / f"{stem}{ext}"
            if p.exists():
                img_path = p
                break
        if img_path is None:
            continue

        iw, ih = _image_size(img_path)
        gts = _load_yolo_labels(labels_dir / f"{stem}.txt", iw, ih, class_names)

        if filter_class is not None:
            preds = [p for p in preds if p.get("detection_class") == filter_class]
            gts   = [g for g in gts   if g.get("detection_class") == filter_class]

        # false positives: pred with high conf but no GT overlap
        fps: list[dict[str, Any]] = []
        for p in preds:
            if float(p.get("detection_confidence", 0.0)) < fp_conf_threshold:
                continue
            pb = tuple(p["bbox_px"])
            best = max((_iou(pb, tuple(g["bbox_px"])) for g in gts), default=0.0)
            if best < iou_threshold:
                fps.append(p)

        # false negatives: GT not matched by any pred
        matched = [False] * len(gts)
        for p in preds:
            pb = tuple(p["bbox_px"])
            for i, g in enumerate(gts):
                if _iou(pb, tuple(g["bbox_px"])) >= iou_threshold:
                    matched[i] = True
        fns = [g for g, ok in zip(gts, matched, strict=True) if not ok]

        if not fps and not fns:
            continue

        # copy image + write GT labels (annotator starting point)
        dst_img = out_dir / "images" / img_path.name
        shutil.copy2(img_path, dst_img)
        lbl_dst = out_dir / "labels" / f"{stem}.txt"
        with open(lbl_dst, "w", encoding="utf-8") as f:
            for g in gts:
                x, y, w, h = g["bbox_px"]
                cx = (x + w / 2) / iw
                cy = (y + h / 2) / ih
                f.write(
                    f"{class_names.index(g['detection_class'])} "
                    f"{cx:.6f} {cy:.6f} {w / iw:.6f} {h / ih:.6f}\n"
                )

        manifest_rows.append({
            "image": dst_img.name,
            "n_false_positives": len(fps),
            "n_false_negatives": len(fns),
            "filter_class": filter_class or "",
        })
        counter["FP"] += len(fps)
        counter["FN"] += len(fns)
        n_copied += 1

    manifest = out_dir / "manifest.csv"
    if manifest_rows:
        with open(manifest, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(manifest_rows[0]))
            w.writeheader()
            w.writerows(manifest_rows)

    return {
        "copied":          n_copied,
        "false_positives": counter["FP"],
        "false_negatives": counter["FN"],
        "manifest":        str(manifest) if manifest_rows else None,
    }


def main() -> int:
    from src.detection.yolo_wrapper import CLASS_NAMES
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--predictions",  type=Path, required=True)
    ap.add_argument("--ground-truth", type=Path, required=True)
    ap.add_argument("--images",       type=Path, required=True)
    ap.add_argument("--out",          type=Path, required=True)
    ap.add_argument("--max-images",   type=int, default=500)
    ap.add_argument("--filter-class", default=None)
    args = ap.parse_args()

    preds = _load_predictions(args.predictions)
    summary = mine(
        predictions=preds,
        labels_dir=args.ground_truth, images_dir=args.images,
        out_dir=args.out, max_images=args.max_images,
        filter_class=args.filter_class, class_names=CLASS_NAMES,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
