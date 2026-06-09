# Phase 2 — Acceptance Checklist

> Per `docs/05_phases.md`, Phase 2 (W3-W5) is "Data". This file is the
> ground-truth checklist of what "Phase 2 done" means in this repo.
> Tick a box only when the artefact exists *and* the verify command exits 0.

## W3 — Public dataset conversion

| # | Deliverable                                              | Artefact                                  | Verify command                                                           | Done |
|---|----------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------|------|
| 1 | DOTA → YOLO converter (7-class taxonomy)                 | `scripts/convert_dota.py`                 | `pytest tests/unit/test_convert_dota.py`                                 | ✅ (W2 carryover) |
| 2 | VEDAI → YOLO converter                                   | `scripts/convert_vedai.py`                | `pytest tests/unit/test_convert_vedai.py`                                | ✅   |
| 3 | xView (GeoJSON) → YOLO converter                          | `scripts/convert_xview.py`                | `pytest tests/unit/test_convert_xview.py`                                | ✅   |
| 4 | Multi-source merger with stratified split + manifest     | `scripts/merge_datasets.py`               | `pytest tests/unit/test_merge_datasets.py`                               | ✅   |
| 5 | Per-source DOTA / VEDAI / xView datasets on disk         | `data/processed/v0.{1,2,3}_*/`            | runs on the dev box (needs the raw datasets)                             | ⏳ ext data |

## W4 — Internal + synthetic data

| # | Deliverable                                              | Artefact                                  | Verify command                                                           | Done |
|---|----------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------|------|
| 6 | Label Studio project template (matches our taxonomy)     | `configs/label_studio_project.xml`        | manual import (UI)                                                       | ✅   |
| 7 | 500 internal images labelled (Person + Vehicle-Tracked)  | `data/annotations/internal_v1/`           | `dataset_stats.py --root data/annotations/internal_v1`                   | ⏳ ext data |
| 8 | AirSim synthetic-data harness                            | `scripts/airsim_collect.py`               | `pytest tests/unit/test_airsim_collect.py`                               | ✅   |
| 9 | Waypoint sample for the synthetic mission                | `configs/airsim_waypoints.json`           | `python scripts/airsim_collect.py --dry-run ...`                         | ✅   |
|10 | 2 000 synthetic images on disk                           | `data/synthetic/airsim_run_001/`          | needs AirSim                                                              | ⏳ ext data |

## W5 — Dataset v1.0 + quality gates

| # | Deliverable                                              | Artefact                                  | Verify command                                                           | Done |
|---|----------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------|------|
|11 | Merged dataset `v1.0` from all sources                   | `data/processed/v1.0/`                    | `merge_datasets.py --src ... --dst data/processed/v1.0`                  | ⏳ ext data |
|12 | Dataset-stats report + all 4 gates pass on v1.0          | `data/processed/v1.0/dataset_stats_report.md` + summary JSON | `python scripts/dataset_stats.py --root data/processed/v1.0` exits 0 | ⏳ ext data |
|13 | Per-class instance count ≥ 500 (G1 from doc 4 §5)         | covered by item 12                        | covered                                                                  | ⏳ ext data |
|14 | `data/processed/current` symlink → `v1.0`                | `data/processed/current`                  | `readlink data/processed/current`                                        | ⏳ ext data |
|15 | DVC tracks v1.0                                          | `data/processed/v1.0.dvc`                 | `dvc status data/processed/v1.0.dvc`                                     | ⏳ ext data |

## Items requiring external data ("ext data")

Items 5, 7, 10–15 cannot complete in the sandbox because they need the
raw DOTA / VEDAI / xView downloads (~30 GB combined) or a running AirSim
instance + labelled internal imagery. The code/CI/tests gates (items 1–4,
6, 8, 9) all pass here. The full pipeline is:

```bash
# 1. Download raw datasets into data/raw/{DOTA,VEDAI,xView}/ (DVC pulls these in prod)
# 2. Convert
python scripts/convert_dota.py  --src data/raw/DOTA              --dst data/processed/v0.1_dota_baseline
python scripts/convert_vedai.py --src data/raw/VEDAI/Annotations1024 \
                                --imgs data/raw/VEDAI/Vehicules1024 \
                                --dst data/processed/v0.2_vedai
python scripts/convert_xview.py --geojson data/raw/xView/xView_train.geojson \
                                --imgs data/raw/xView/train_images \
                                --dst data/processed/v0.3_xview

# 3. Synthetic (W4)
python scripts/airsim_collect.py --run-id airsim_run_001 \
    --waypoints configs/airsim_waypoints.json \
    --dst data/synthetic/airsim_run_001 --n-frames 2000

# 4. Merge into v1.0
python scripts/merge_datasets.py \
    --src data/processed/v0.1_dota_baseline:dota \
          data/processed/v0.2_vedai:vedai \
          data/processed/v0.3_xview:xview \
          data/synthetic/airsim_run_001:synthetic \
          data/annotations/internal_v1:internal \
    --dst data/processed/v1.0 --splits 0.8 0.1 0.1

# 5. Quality gates (must exit 0)
python scripts/dataset_stats.py --root data/processed/v1.0

# 6. Version with DVC
dvc add data/processed/v1.0
git add data/processed/v1.0.dvc && git commit -m "phase-2: dataset v1.0"
dvc push
```

## Sign-off

Phase 2 closes when:
- All items 1, 2, 3, 4, 6, 8, 9 ✅ (sandbox: CI-verifiable).
- The 5/7/10/11/12/13/14/15 items are ticked on the dev box.
- A new `DECISIONS.md` entry under category `Data` titled "Phase 2 closed:
  dataset v1.0" cites the final per-class instance counts.
