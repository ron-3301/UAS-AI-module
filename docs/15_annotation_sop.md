# DOCUMENT 15: ANNOTATION STANDARD OPERATING PROCEDURE

> Doc 3 references `data/annotations/` and "annotation SOP checklists" but never defines them. This document is the SOP.

## 1. Tooling
- **Label Studio** (self-hosted, Docker, see `docker-compose.yml`).
- One project per dataset version (e.g. `uas_v1.2`).
- Export format: **YOLO** (one .txt per image, normalised xywh).

## 2. Per-Image Checklist (must all be true before saving)
1. Every visible object belonging to the 7 classes in Doc 11 has a box.
2. Boxes are **tight**: ≤ 2-pixel margin on each side at native resolution.
3. Truncated objects (cut by image edge) are still annotated if ≥ 50 % visible; otherwise skipped and the image is tagged `partial_truncation`.
4. Heavily occluded objects (< 30 % visible) are skipped and the image tagged `heavy_occlusion`.
5. Sub-label (for Layer 3 classifier) is assigned via Label Studio's `choices` widget — one per box. If unsure, choose `Unknown` (do **not** guess).
6. Image-level tags applied where relevant: `night`, `rain`, `snow`, `camouflage`, `low_contrast`, `motion_blur`, `synthetic`.

## 3. Inter-Annotator Agreement
- 10 % of images are double-annotated.
- Compute box-level IoU and class agreement weekly via `scripts/iaa_report.py`.
- Acceptance: mean IoU ≥ 0.85, class agreement ≥ 95 %. Below that, hold a calibration meeting and re-annotate the disputed batch.

## 4. Hand-off to Dataset
Each annotator session ends by exporting to `data/annotations/{annotator_id}/{date}/`. The lead reviewer then:
1. Runs `scripts/merge_annotations.py` → merges into `data/processed/v{X}.{Y}/`.
2. Runs `scripts/dataset_stats.py` (gates from Doc 4 §5).
3. Updates `data/processed/v{X}.{Y}/CHANGELOG.md`.
4. `dvc add data/processed && dvc push && git commit`.
5. Adds a `DECISIONS.md` entry (Category: Data) if class balance, splits, or taxonomy changed.

## 5. Edge Cases (rulings — append to `data/annotations/SOP_rulings.md` when new)
- Mannequins, statues, mannequin-on-vehicle → **not** `Person`.
- Civilian SUV with mounted machine gun → `Vehicle-Wheeled` + sub-label `Civilian-Truck` (override = 0.15) UNLESS armed combatants visible inside → sub-label `Toyota-Hilux` (technical).
- Helicopter under camouflage netting on the ground → `Aircraft-Rotary` + image tag `camouflage`.
- Burnt-out / destroyed tank hulk → `Vehicle-Tracked` + sub-label `Unknown`, image tag `destroyed`. (These are training negatives for "is a threat" downstream but positive for "is a tank" detection.)
