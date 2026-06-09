# Phase 3 — Acceptance Checklist

> Per `docs/05_phases.md`, Phase 3 (W6-W9) is "Detection".  Tick a box only
> when the artefact exists *and* the verify command exits 0.

## W6 — Architecture selection + working pipeline

| # | Deliverable                                                                | Artefact                                                                 | Verify command                                                            | Done |
|---|----------------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------------|------|
| 1 | Detector wrapper (Ultralytics) + mock detector for tests                   | `src/detection/yolo_wrapper.py`                                          | `pytest tests/integration/test_pipeline_end_to_end.py`                    | ✅   |
| 2 | Class-agnostic NMS at IoU=0.45                                             | `src/detection/nms.py`                                                    | `pytest tests/unit/test_nms.py`                                           | ✅   |
| 3 | IoU tracker (ByteTrack-shape API)                                          | `src/detection/tracker.py`                                                | `pytest tests/unit/test_tracker.py`                                       | ✅   |
| 4 | Crop extractor with padding + resize                                       | `src/identification/crop_extractor.py`                                    | `pytest tests/unit/test_crop_extractor.py`                                | ✅   |
| 5 | Classifier wrapper (ONNX) + mock classifier                                | `src/identification/classifier.py`                                        | covered by pipeline tests                                                  | ✅   |
| 6 | Frame capture (OpenCV) with retry policy                                   | `src/ingestion/frame_capture.py`                                          | `pytest tests/unit/test_frame_capture.py`                                 | ✅   |
| 7 | MAVLink telemetry parser with ring buffer                                  | `src/ingestion/telemetry_parser.py`                                       | `pytest tests/unit/test_telemetry_sync.py`                                | ✅   |
| 8 | Frame ↔ telemetry synchroniser (docs/13 §4)                                | `src/ingestion/sync.py`                                                   | covered by `test_telemetry_sync.py`                                       | ✅   |
| 9 | Pipeline orchestrator wiring all 5 layers                                  | `src/pipeline.py`                                                         | `pytest tests/integration/`                                               | ✅   |
|10 | UDP emitter + InMemoryEmitter + chained()                                  | `src/output/udp_emitter.py`                                               | `pytest tests/unit/test_udp_emitter.py`                                   | ✅   |
|11 | **End-to-end pipeline runs on synthetic frames; safety contract still fires** | `tests/integration/test_pipeline_end_to_end.py`                       | `pytest tests/integration/test_pipeline_end_to_end.py -v`                | ✅   |
|12 | Model benchmark harness (mAP + latency table, recommends winner)           | `scripts/benchmark_models.py`                                             | `pytest tests/unit/test_benchmark_models.py`                              | ✅   |
|13 | Benchmark actually run on data/processed/v1.0; winner picked               | `runs/w6_benchmark/benchmark.md`                                          | needs GPU + v1.0 dataset                                                   | ⏳ ext |

## W7 — Hyperparameter search

| # | Deliverable                                                                | Artefact                                                                 | Verify command                                                            | Done |
|---|----------------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------------|------|
|14 | Optuna study with TPE sampler + median pruner                              | `training/hyperparam_search.py`                                           | `pytest tests/unit/test_hyperparam_search.py`                             | ✅   |
|15 | 50-trial study completed on chosen detector; summary.json saved            | `runs/w7_hpo/summary.json`                                                | needs GPU                                                                  | ⏳ ext |

## W8 — Full training + evaluation

| # | Deliverable                                                                | Artefact                                                                 | Verify command                                                            | Done |
|---|----------------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------------|------|
|16 | Evaluator: mAP@50, mAP@50-95, per-class AP, confusion matrix, markdown report | `training/eval.py`                                                    | `pytest tests/unit/test_eval.py`                                          | ✅   |
|17 | Full 300-epoch training run with the W7 winner hyperparameters             | `runs/detector/full_v1/`                                                  | needs GPU                                                                  | ⏳ ext |
|18 | mAP@50 ≥ 0.80 on the test split                                            | `runs/eval/results.json::map50`                                           | needs GPU                                                                  | ⏳ ext |

## W9 — Error analysis + hard-negative loop

| # | Deliverable                                                                | Artefact                                                                 | Verify command                                                            | Done |
|---|----------------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------------|------|
|19 | Hard-negative miner: surfaces FP and FN images, copies + writes YOLO labels | `scripts/mine_hard_negatives.py`                                         | `pytest tests/unit/test_mine_hard_negatives.py`                           | ✅   |
|20 | 500 hard negatives collected for the worst-AP class; retrain → ≥ 0.80      | `data/annotations/active_learning_batch_001/`                            | needs annotators + GPU                                                     | ⏳ ext |

## Sign-off

Phase 3 closes when items 1–12, 14, 16, 19 ✅ (sandbox: CI-verifiable, done)
**and** items 13, 15, 17, 18, 20 ticked on the dev GPU box. The full
recipe with shell commands is below.

```bash
# W6 — pick the winner
python scripts/benchmark_models.py \
    --data data/processed/current/data.yaml --epochs 30 \
    --device 0 --out-dir runs/w6_benchmark

# W7 — search hyperparams for the winner
python training/hyperparam_search.py \
    --data data/processed/current/data.yaml --arch <winner> \
    --trials 50 --trial-epochs 15 --device 0 \
    --study-name w7 --storage sqlite:///runs/optuna.db \
    --out runs/w7_hpo/summary.json

# W8 — train for real with the best HPO trial, then evaluate
python training/train_detector.py \
    --config configs/training.yaml --data data/processed/current/data.yaml \
    --arch <winner> --epochs 300 --name full_v1 --device 0
python training/eval.py --weights runs/detector/full_v1/weights/best.pt \
    --data data/processed/current/data.yaml --out-dir runs/eval

# W9 — if eval fails the 0.80 gate, mine hard negatives for the worst class
python scripts/mine_hard_negatives.py \
    --predictions runs/eval/predictions/ \
    --ground-truth data/processed/current/labels/val/ \
    --images       data/processed/current/images/val/ \
    --out          data/annotations/active_learning_batch_001/ \
    --max-images 500 --filter-class <worst_class>
# Annotators run through Label Studio, then re-train on the bumped dataset.
```
