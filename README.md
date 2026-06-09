# uas-ai-module

On-board AI payload for a UAS. Watches the camera feed in real time, detects
ground objects, identifies them more specifically, geolocates each one on the
map, and emits a JSON targeting recommendation to the ground station.

Runs locally on an NVIDIA Jetson Orin NX at roughly 110 ms p95 latency
end-to-end. No internet needed during a mission - everything happens on board.

## What it does

Five layers wired together:

1. **Ingestion** - opens the camera (RTSP / USB / GStreamer), reads MAVLink
   telemetry over UDP, matches each frame to the nearest telemetry sample.
2. **Detection** - YOLOv8m, 7 classes: Person, Vehicle-Wheeled,
   Vehicle-Tracked, Aircraft-Rotary, Aircraft-Fixed, Watercraft, Structure-Temp.
3. **Identification** - EfficientNet-B3 (ONNX) on the cropped detections,
   produces a fine-grained sub-label like "Humvee" or "Civilian-Sedan".
4. **Geolocation** - pinhole ray-cast to a terrain plane, per-track Kalman
   filter on the world-space coordinate. Outputs lat/lon with an error
   estimate (CEP).
5. **Output** - JSON over UDP to the ground station, annotated video over
   RTSP, SQLite mission log on disk.

Plus a threat scorer that combines detection confidence, ID confidence,
slant range, motion, and mission context into a single score.

## Important: this module is advisory only

It never controls a weapon, never moves the drone, never bypasses an
autopilot. It emits *recommendations*. The downstream system keeps all
final authority.

It also has hard-coded safety filters that **cannot be turned off via
config**. They live as constants in `src/output/json_serializer.py`:

| Filter | Threshold |
|--------|-----------|
| Detection confidence floor | 0.30 - below this, dropped |
| Civilian sub-label | dropped if `id_conf > 0.50` |
| Person at low altitude | dropped if `alt_agl_m < 30 m` |
| Bad geolocation | kept but `validity_flag = false` if `cep_m > 25 m` |

Changing these requires editing source code, not YAML. There are unit tests
that lock these thresholds (`tests/unit/test_json_serializer.py`) - if
someone tries to weaken them, the test suite will tell you.

## Hardware target

- NVIDIA Jetson Orin NX 16 GB, JetPack 6.0+
- camera over CSI, USB, or RTSP
- MAVLink 2.0 telemetry on UDP port 14550 (configurable)
- ground station reachable by UDP (configurable address/port)

Development is done on x86 with Docker.

## Repo layout

```
src/                # the 5 pipeline layers + orchestrator + CLI
    ingestion/      # frame capture, telemetry parser, sync
    detection/      # YOLO wrapper, NMS, tracker
    identification/ # classifier, crop extractor, threat scorer
    geolocation/    # ray-caster, Kalman, coord conversions
    output/         # JSON serializer (safety filters), UDP, SQLite, RTSP
    pipeline.py     # wires it all together
    cli.py          # `python -m src.cli --config configs/inference.yaml`

training/           # train_detector, train_classifier, eval, hyperparam_search
scripts/            # data converters, dataset stats, hard-negative miner, etc.
configs/            # inference / training / camera / class-weights yamls + schemas
tests/              # unit + integration. mostly stand-alone (no GPU needed)
data/               # DVC-tracked. raw / processed / synthetic. NEVER commit.
models/             # weights + TRT engines. NEVER commit.
```

## Quick start (dev box)

You need Python 3.10+ and Docker.

```bash
# 1. install deps
make install

# 2. run every CI-runnable gate (lint + tests + config validation)
make verify-phase1   # foundations
make verify-phase2   # data pipeline
make verify-phase3   # detection pipeline end-to-end

# 3. quick sanity check the CLI loads + validates a config
python -m src.cli --config configs/inference.yaml --dry-run

# 4. full dev stack (AI module + MQTT broker + Label Studio)
docker compose up -d
```

If `make verify-phase3` passes, the whole code path runs end-to-end on CPU
with no weights via the mock detector + mock classifier. That's the
integration test - 75 tests, ~2 seconds. If something breaks later, this is
the first thing to run.

## Configuration

YAML files in `configs/`, validated against JSON schemas in
`configs/schemas/`. Precedence, highest to lowest:

1. `--override key=value` on the CLI (repeatable)
2. environment variables: `UAS_MODEL__DETECTION_CONF_THRESHOLD=0.6` etc
3. the YAML file
4. built-in defaults in `src/config.py`

Every YAML has a `version` field. Loader fails fast if the major version
isn't 1, and if the schema doesn't match.

## Data pipeline

Datasets live in `data/`, tracked by DVC, never committed to Git.

Workflow:

```bash
# convert public datasets to YOLO format using our 7-class taxonomy
python scripts/convert_dota.py  --src data/raw/DOTA  --dst data/processed/v0.1_dota
python scripts/convert_vedai.py --src data/raw/VEDAI/Annotations1024 \
                                --imgs data/raw/VEDAI/Vehicules1024 \
                                --dst data/processed/v0.2_vedai
python scripts/convert_xview.py --geojson data/raw/xView/xView_train.geojson \
                                --imgs    data/raw/xView/train_images \
                                --dst     data/processed/v0.3_xview

# merge into one stratified, deduplicated dataset
python scripts/merge_datasets.py \
    --src data/processed/v0.1_dota:dota \
          data/processed/v0.2_vedai:vedai \
          data/processed/v0.3_xview:xview \
    --dst data/processed/v1.0

# quality gates - non-zero exit if any class is under-represented, has tiny
# boxes, duplicate images, or class leakage between train/val/test splits
python scripts/dataset_stats.py --root data/processed/v1.0

# version it
dvc add data/processed/v1.0
git add data/processed/v1.0.dvc && git commit -m "dataset v1.0"
dvc push
```

`data/processed/current` is a symlink to whichever version you're training
against. The merger refreshes it automatically.

## Training

```bash
# baseline detector (W2 proof-of-pipeline, ~2 hrs on one A100)
python training/train_detector.py \
    --config configs/training.yaml \
    --data   data/processed/current/data.yaml \
    --arch   yolov8n --epochs 50 --name baseline

# pick the best detector architecture (W6, runs all 4 candidates)
python scripts/benchmark_models.py \
    --data data/processed/current/data.yaml \
    --epochs 30 --device 0 --out-dir runs/w6_benchmark

# hyperparameter search on the winner (W7, 50 trials)
python training/hyperparam_search.py \
    --data data/processed/current/data.yaml \
    --arch yolov8m --trials 50 --trial-epochs 15 \
    --study-name w7 --storage sqlite:///runs/optuna.db

# full training, then eval (W8, target mAP@50 >= 0.80)
python training/train_detector.py \
    --config configs/training.yaml --data data/processed/current/data.yaml \
    --arch yolov8m --epochs 300 --name full_v1
python training/eval.py \
    --weights runs/detector/full_v1/weights/best.pt \
    --data    data/processed/current/data.yaml \
    --out-dir runs/eval

# if eval misses the gate, mine hard negatives for the worst class (W9)
python scripts/mine_hard_negatives.py \
    --predictions  runs/eval/predictions/ \
    --ground-truth data/processed/current/labels/val/ \
    --images       data/processed/current/images/val/ \
    --out          data/annotations/active_learning_batch_001/ \
    --max-images 500 --filter-class Person
```

Every training / eval / benchmark script has a `--dry-run` mode that
short-circuits the heavy GPU call and returns deterministic synthetic
numbers. CI uses these so the report writers and Optuna plumbing get
exercised on every commit without needing a GPU.

## Deploy to Jetson

```bash
# build the Jetson image (on the Jetson, not on x86)
docker build --target jetson -t uas-ai:jetpack6 .

# build the TensorRT engines from the ONNX models (architecture-specific,
# must be done on the actual hardware)
./scripts/build_trt_engines.sh

# run with GPU + camera + serial
docker run --runtime=nvidia \
    --device /dev/video0 --device /dev/ttyUSB0 \
    -v /path/to/models:/workspace/models \
    -v /path/to/logs:/workspace/logs \
    -p 5005:5005/udp -p 8554:8554 -p 8080:8080 \
    uas-ai:jetpack6
```

Use `--network=host` for lowest-latency ZeroMQ / RTSP if you trust the
network. On the Jetson, set `nvpmodel -m 1` for the 25 W power mode (the
default flight profile).

## API

**Input:** MAVLink 2.0 over UDP 14550 - `GLOBAL_POSITION_INT`, `ATTITUDE`,
`VFR_HUD`. Tolerates up to 1 second of missing data before flagging packets
as stale.

**Output:** JSON over UDP, default port 5005. One packet per frame:

```json
{
  "schema_version": "1.0",
  "mission_id": "MSN-20260615-001",
  "frame_id": 4821,
  "timestamp_utc": "2026-06-15T09:32:14.823Z",
  "uas_telemetry": { "lat": 51.5074, "lon": -0.1278, "alt_agl_m": 98.7 },
  "validity_flag": true,
  "detections": [
    {
      "detection_id": "d_4821_001",
      "track_id": 17,
      "bbox_px": [842, 391, 122, 56],
      "detection_class": "Vehicle-Wheeled",
      "detection_confidence": 0.91,
      "identification": { "label": "Humvee", "confidence": 0.84 },
      "geolocation":    { "lat": 51.507612, "lon": -0.128043, "cep_m": 3.8 },
      "threat_score":   0.73
    }
  ]
}
```

When there's nothing to report: `{"detections": []}`. When something goes
wrong: the packet still gets emitted, with `validity_flag: false` and an
`error` field with one of these codes:

- 100 - camera stream timeout
- 101 - telemetry sync lost
- 102 - GPS denied (visual-odometry fallback active)
- 103 - model inference failed (fell back to CPU)

Also: HTTP `/health` on port 8080 returns uptime, FPS, last error, GPU
memory. MQTT secondary channel on the topics `uas/{uas_id}/targets`,
`/health`, `/error`, `/heartbeat`.

## Performance budget

Total: <=110 ms p95 on the Jetson at 25 W. Per stage:

| stage | budget (ms) |
|-------|------:|
| frame capture + decode    | 12 |
| pre-processing            | 4  |
| detector inference (INT8) | 45 |
| NMS + tracker             | 5  |
| classifier (top-K crops)  | 15 |
| geolocation               | 3  |
| serialise + send + log    | 4  |
| **total**                 | **88** |

The remaining ~22 ms is headroom for jitter. If p95 exceeds 110 ms for >30s,
the pipeline auto-downscales (640 -> 480 input) and logs a degradation
event. If it still misses, it drops the classifier every other frame.
Thermal throttling triggers the same fallback chain at 80 °C junction temp.

## Testing

```bash
make test          # unit tests
make test-cov      # with coverage (gate: 85%)
make lint          # ruff
make typecheck     # mypy
```

The integration test (`tests/integration/test_pipeline_end_to_end.py`) is
the keystone - it runs 10 frames through the full pipeline with a mock
detector + mock classifier and asserts:

- one emitted packet per input frame
- track IDs are stable across frame-to-frame drift
- per-stage timing is recorded
- the civilian-suppression safety contract still fires end-to-end

If you only have time to run one test before pushing, run that one.

## Development workflow

- All decisions (architecture, library choices, threshold values) live in
  `DECISIONS.md`. Append-only. New entry every time you make a non-obvious
  choice. Before starting a session, read the last few entries.
- All training / eval / benchmark scripts support `--dry-run`. Use it.
- All YAML configs are schema-validated. If you add a YAML file, add its
  schema in `configs/schemas/` - a test enforces this.
- Hard-coded safety thresholds in `src/output/json_serializer.py` are not
  configurable. If you genuinely need to change one, write a new DECISIONS
  entry first.

## Export-control note

UAS object-recognition + targeting code can fall under ITAR / EAR /
Wassenaar dual-use regulations depending on jurisdiction. Talk to whoever
does compliance at your org before pushing this to a public repo or
sharing the weights externally.

## Status

| phase | status | notes |
|-------|--------|-------|
| 1 - Foundations               | done       | items 1-14 verified by `make verify-phase1`. item 15 (baseline mAP) needs GPU + DOTA. |
| 2 - Data pipeline             | in flight  | CI gates pass. converters + merger + AirSim harness ready. waiting on raw downloads. |
| 3 - Detection                 | in flight  | CI gates pass. end-to-end pipeline runs on CPU with mocks. waiting on GPU for real training. |
| 4 - Identification + geo      | todo       |   |
| 5 - Edge optimisation         | todo       |   |
| 6 - Testing + adversarial     | todo       |   |
