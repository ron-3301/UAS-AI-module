# uas-ai-module

On-board AI payload for a UAS. Watches the camera feed in real time, detects ground objects, identifies them more specifically, geolocates each one on the map, and emits a JSON targeting recommendation to the ground station.

Runs locally on an NVIDIA Jetson Orin NX at roughly 110 ms p95 latency end-to-end. No internet is needed during a mission - everything happens on board.

## What it does

Five layers wired together:

1. **Ingestion**  
   Opens the camera (RTSP / USB / GStreamer), reads MAVLink telemetry over UDP, and matches each frame to the nearest telemetry sample using time synchronisation.

2. **Detection**  
   Runs YOLOv8m to detect seven object classes: Person, Vehicle-Wheeled, Vehicle-Tracked, Aircraft-Rotary, Aircraft-Fixed, Watercraft, and Structure-Temp.

3. **Identification**  
   Crops detected objects and passes them through an EfficientNet-B3 classifier (exported to ONNX) to produce fine-grained sub-labels such as "Humvee", "Civilian-Sedan", or "Attack-Helicopter".

4. **Geolocation**  
   Uses a pinhole camera model to ray-cast detections onto a terrain plane. A per-track Kalman filter smooths the resulting world-space coordinates and produces a circular error probable (CEP) estimate.

5. **Output**  
   Serialises results into a JSON packet sent over UDP to the ground station. Also generates annotated video over RTSP and writes a full mission log to SQLite.

A threat scorer combines detection confidence, identification confidence, slant range, motion, and mission context into a single numeric score for each detection.

## Important: this module is advisory only

The system never controls weapons, never moves the drone, and never bypasses an autopilot. It only emits recommendations. The downstream system retains all final authority.

Hard-coded safety filters that cannot be disabled via configuration live in src/output/json_serializer.py:

| Filter                        | Threshold                                      |
|-------------------------------|------------------------------------------------|
| Detection confidence floor    | 0.30 - detections below this are dropped       |
| Civilian sub-label            | dropped if identification confidence > 0.50    |
| Person at low altitude        | dropped if altitude above ground level < 30 m  |
| Bad geolocation               | validity_flag set to false if CEP > 25 m       |

These thresholds are locked by unit tests. Changing them requires editing source code and updating the corresponding tests.

## Hardware target

- NVIDIA Jetson Orin NX 16 GB, JetPack 6.0 or newer
- Camera input over CSI, USB, or RTSP
- MAVLink 2.0 telemetry on UDP port 14550 (configurable)
- Ground station reachable by UDP (configurable address and port)

Development is performed on x86 machines using Docker. Deployment to the Jetson uses a multi-stage Dockerfile.

## Repository layout

```
src/
    ingestion/          frame capture, telemetry parser, synchronisation
    detection/          YOLO wrapper, NMS, tracker
    identification/     classifier, crop extractor, threat scorer
    geolocation/        ray-caster, Kalman filter, coordinate conversions
    output/             JSON serializer (safety filters), UDP emitter, SQLite logger, RTSP annotator
    pipeline.py         orchestrates the five layers
    cli.py              command-line interface
training/
    train_detector.py
    train_classifier.py
    eval.py
    hyperparam_search.py
scripts/
    convert_dota.py, convert_vedai.py, convert_xview.py
    merge_datasets.py, dataset_stats.py
    benchmark_models.py, mine_hard_negatives.py
    build_trt_engines.sh, benchmark_latency.py, thermal_soak_test.py
    robustness_sweep.py, failure_injection_test.py, adversarial_eval.py
configs/
    inference.yaml, identification_labels.yaml
```

## Quick start

Install dependencies and verify the pipeline:

```bash
python -m src.cli --config configs/inference.yaml --dry-run
```

Every heavy script supports a --dry-run flag that returns deterministic synthetic results so continuous integration can exercise the full code path without a GPU.

## Configuration

YAML files live in configs/ and are validated against JSON schemas. Configuration precedence (highest to lowest):

1. --override key=value on the command line
2. Environment variables (UAS__SECTION__KEY)
3. The YAML file itself
4. Built-in defaults in src/config.py

Every YAML file contains a version field. The loader fails fast if the major version is not 1 or if the schema does not match.

## Data pipeline

Public datasets are converted to a common 7-class taxonomy, merged, and quality-gated. The workflow is:

```bash
python scripts/convert_dota.py --src data/raw/DOTA --dst data/processed/v0.1_dota
python scripts/convert_vedai.py --src data/raw/VEDAI --imgs data/raw/VEDAI/imgs --dst data/processed/v0.2_vedai
python scripts/convert_xview.py --geojson data/raw/xView/train.geojson --imgs data/raw/xView/imgs --dst data/processed/v0.3_xview

python scripts/merge_datasets.py --src v0.1 v0.2 v0.3 --dst data/processed/v1.0
python scripts/dataset_stats.py --root data/processed/v1.0
```

The merger produces a stratified 80/10/10 split and a manifest.csv recording provenance. data/processed/current is a symlink pointing to the active version.

## Training

Baseline detector training, architecture benchmarking, hyperparameter search, full training, evaluation, and hard-negative mining are all scripted:

```bash
python training/train_detector.py --config configs/training.yaml --data data/processed/current/data.yaml --arch yolov8n --epochs 50 --name baseline
python scripts/benchmark_models.py --data data/processed/current/data.yaml --epochs 30 --device 0 --out-dir runs/w6_benchmark
python training/hyperparam_search.py --data data/processed/current/data.yaml --arch yolov8m --trials 50 --trial-epochs 15 --study-name w7
python training/train_detector.py --config configs/training.yaml --data data/processed/current/data.yaml --arch yolov8m --epochs 300 --name full_v1
python training/eval.py --weights runs/detector/full_v1/weights/best.pt --data data/processed/current/data.yaml --out-dir runs/eval
python scripts/mine_hard_negatives.py --predictions runs/eval/predictions/ --ground-truth data/processed/current/labels/val/ --images data/processed/current/images/val/ --out data/annotations/active_learning_batch_001/ --max-images 500 --filter-class Person
```

All training and evaluation scripts support --dry-run.

## Deployment to Jetson

Build TensorRT engines on the target hardware, then run the container:

```bash
./build_trt_engines.sh
docker run --runtime=nvidia --device /dev/video0 --device /dev/ttyUSB0 -v /path/to/models:/workspace/models uas-ai:jetpack6
```

On the Jetson, set nvpmodel -m 1 for the 25 W flight profile.

## API

Input: MAVLink 2.0 messages (GLOBAL_POSITION_INT, ATTITUDE, VFR_HUD) on UDP 14550.

Output: One JSON packet per frame on UDP 5005. Example packet:

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
      "geolocation": { "lat": 51.507612, "lon": -0.128043, "cep_m": 3.8 },
      "threat_score": 0.73
    }
  ]
}
```

Error codes 100-103 are used when the pipeline degrades gracefully.

## Performance budget

Target: ≤110 ms p95 on the Jetson at 25 W. Nominal per-stage budget sums to 88 ms.

| Stage                         | Budget (ms) |
|-------------------------------|-------------|
| Frame capture + decode        | 12          |
| Pre-processing                | 4           |
| Detector inference (INT8)     | 45          |
| NMS + tracker                 | 5           |
| Classifier (top-K crops)      | 15          |
| Geolocation                   | 3           |
| Serialise + send + log        | 4           |
| Total                         | 88          |

If p95 exceeds 110 ms for more than 30 seconds, the pipeline automatically downscales input resolution and may skip the classifier. Thermal throttling at 80 °C junction temperature triggers the same fallback chain.

## Development workflow

- All non-obvious decisions are recorded in DECISIONS.md (append-only).
- Every training, evaluation, and benchmark script supports --dry-run.
- New YAML files require a matching JSON schema in configs/schemas/.
- Hard-coded safety thresholds are not configurable through YAML.

## What not to commit

Never commit credentials, real flight logs, mission SQLite files, or video/images from actual missions. Raw data, trained weights, and TensorRT engines belong in DVC or are never committed.

## Export-control note

UAS object-recognition and targeting code can fall under ITAR, EAR, or Wassenaar dual-use regulations depending on jurisdiction. Obtain compliance review before any public repository or external weight sharing.

## Status

All six phases of the project plan have been completed:

| Phase                        | Status |
|------------------------------|--------|
| 1 - Foundations              | done   |
| 2 - Data pipeline            | done   |
| 3 - Detection                | done   |
| 4 - Identification + geo     | done   |
| 5 - Edge optimisation        | done   |
| 6 - Testing + adversarial    | done   |