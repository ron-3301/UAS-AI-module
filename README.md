# UAS AI Module

A safety-first, advisory-only UAS perception and validation module for camera-frame ingestion, telemetry ingestion, object-detection advisories, geolocation, deterministic replay, dataset conversion, model-governance preparation, and external integration testing.

The module is designed to support lawful monitoring, inspection, research, test and evaluation, and operator decision-support workflows. It does not command a vehicle, upload missions, change flight modes, control actuators, or perform engagement actions.

---

## Table of Contents

- [Purpose](#purpose)
- [Safety Model](#safety-model)
- [System Architecture](#system-architecture)
- [Runtime Data Flow](#runtime-data-flow)
- [Repository Layout](#repository-layout)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Validation](#validation)
- [Runtime Modes](#runtime-modes)
- [Dataset Tooling](#dataset-tooling)
- [Model Governance](#model-governance)
- [External Integration](#external-integration)
- [Output Format](#output-format)
- [Development Rules](#development-rules)
- [Known Limitations](#known-limitations)

---

## Purpose

The UAS AI Module provides a structured software foundation for building and validating an advisory perception pipeline for unmanned aircraft systems.

It can:

1. Read frames from mock, replay, file, video, or OpenCV camera sources.
2. Read telemetry from mock, replay, or read-only MAVLink sources.
3. Run object detection through mock, ONNX Runtime, or TensorRT-boundary interfaces.
4. Optionally classify cropped detections.
5. Estimate object geolocation using camera geometry and terrain hooks.
6. Maintain lightweight local track IDs.
7. Emit advisory-only JSON packets.
8. Validate outputs against versioned schemas.
9. Run deterministic replay and golden-output regression checks.
10. Convert DOTA, VEDAI, and xView-style annotations into a common format.
11. Prepare dataset manifests, model export plans, model metadata, release manifests, and SBOMs.
12. Provide smoke-test scripts for SITL, camera, ONNX, TensorRT, and observability validation.

---

## Safety Model

The project is advisory-only by design.

The runtime must not:

- send MAVLink commands
- upload missions
- change vehicle mode
- control actuators
- command payloads
- perform engagement actions
- provide an autonomous control path

The advisory serializer applies hard-coded safety filters that are intentionally not configurable:

| Rule | Behavior |
|---|---|
| Detection confidence below `0.30` | Detection is dropped |
| Civilian identity confidence above `0.50` | Detection is suppressed |
| Person detection below `30 m AGL` | Detection is dropped |
| CEP above `25 m` | Detection remains emitted but `validity_flag=false` |
| Stale frame | Emitted detections are invalidated |
| Stale telemetry | Emitted detections are invalidated |

All advisory packets include:

```json
"advisory_only": true
```

Caller-supplied recommendations are also forced back to advisory-only form.

---

## System Architecture

```text
                               +---------------------------+
                               |  Config and Schema Layer  |
                               |  JSON/YAML validation     |
                               +-------------+-------------+
                                             |
                                             v
+------------------+       +-----------------+-----------------+       +-------------------+
| Frame Ingestion  |       |        Runtime Pipeline           |       | Telemetry Ingest  |
| mock             | ----> | detection                         | <---- | mock              |
| replay           |       | optional classification           |       | replay            |
| file/image/video |       | tracking                          |       | read-only MAVLink |
| OpenCV camera    |       | geolocation                       |       +-------------------+
+------------------+       | safety filtering                  |
                           | advisory serialization            |
                           +-----------------+-----------------+
                                             |
                                             v
                         +-------------------+-------------------+
                         | Advisory Output Layer               |
                         | JSON packets                        |
                         | schema validation                   |
                         | JSONL logging                       |
                         | metrics extraction                  |
                         +-------------------+-------------------+
                                             |
                                             v
                         +-------------------+-------------------+
                         | Validation and Governance           |
                         | replay and golden tests             |
                         | dataset converters                  |
                         | model metadata                      |
                         | release manifest and SBOM           |
                         | external integration plans          |
                         +---------------------------------------+
```

---

## Runtime Data Flow

A single pipeline iteration performs the following steps:

1. Read one frame.
2. Read the latest telemetry.
3. Run the detector backend.
4. Assign or preserve local track IDs.
5. Optionally crop detections and classify them.
6. Estimate geolocation.
7. Evaluate runtime health and staleness.
8. Apply hard-coded safety filters.
9. Emit advisory JSON.
10. Optionally validate output schema, log the packet, or extract metrics.

The main orchestrator is:

```text
src/uas_ai_module/pipeline.py
```

---

## Repository Layout

```text
src/uas_ai_module/
  cli.py                         Command line entrypoint
  config.py                      Config loading and schema validation
  health.py                      Runtime health and staleness checks
  models.py                      Core runtime dataclasses
  pipeline.py                    End-to-end advisory pipeline
  runtime_factory.py             Config-to-runtime component builders

  ingestion/
    frame_capture.py             Mock frame source
    telemetry_parser.py          Mock telemetry source
    replay.py                    Deterministic replay ingestion
    file_source.py               File and video frame sources
    camera.py                    OpenCV camera boundary
    mavlink.py                   Read-only MAVLink telemetry boundary

  detection/
    detector.py                  Detector protocol and mock detector
    nms.py                       IoU and non-maximum suppression
    onnx_detector.py             ONNX Runtime detector wrapper
    tensorrt_detector.py         TensorRT engine boundary

  identification/
    classifier.py                Mock and ONNX classifier wrappers
    crop_extractor.py            Detection crop extraction

  geolocation/
    raycaster.py                 Basic flat-ground raycaster
    attitude_raycaster.py        Attitude-aware terrain-hook raycaster
    terrain.py                   Flat/grid terrain providers
    transforms.py                Rotation and pinhole helpers

  tracking/
    track_manager.py             Lightweight local track IDs

  prediction/
    tcpa.py                      Time-to-closest-point helper

  output/
    json_serializer.py           Advisory JSON serializer and safety filters
    schema_validator.py          Output schema validation
    jsonl_logger.py              Local JSONL advisory logging
    golden.py                    Golden replay normalization

  metrics/
    runtime_metrics.py           Runtime metric extraction and Prometheus text

  data/
    annotations.py               Common annotation model
    dataset_manifest.py          Dataset governance manifest
    export_plan.py               Model export plan governance
    taxonomy.py                  Taxonomy mapping helpers
    yolo_export.py               YOLO label export
    converters/                  DOTA, VEDAI, and xView converters

  integration/
    external_validation.py       External validation plan parser

  release/
    source_manifest.py           Source SHA-256 manifest
    sbom.py                      Requirements-based SBOM
```

Additional directories:

```text
schemas/                         JSON schemas
configs/                         Example configs and manifests
scripts/                         Validation, conversion, and smoke-test CLIs
training/                        x86-only training/export entrypoints
tests/                           Unit, regression, and integration-style tests
deploy/                          systemd, logrotate, and Mosquitto examples
models/                          Example model manifests and metadata
```

---

## Installation

### Runtime-oriented install

Use the runtime requirements for Jetson or deployment-like environments:

```bash
python -m pip install -r requirements/requirements-runtime.txt
```

Runtime requirements intentionally exclude PyTorch-family packages.

### Development install

For local development and tests:

```bash
python -m pip install -e .
python -m pip install pytest jsonschema PyYAML numpy
```

For x86 training and export preparation only:

```bash
python -m pip install -r requirements/requirements-dev.txt
```

Do not install development/training requirements on the Jetson runtime image unless intentionally building models there.

---

## Quick Start

Run a mocked advisory pipeline:

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --dry-run \
  --validate-output-schema \
  --pretty
```

Run deterministic replay:

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --replay tests/fixtures/replay/sample_mission.json \
  --replay-steps 2 \
  --validate-output-schema
```

Run one config-built pipeline pass with mock backends:

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --run-once \
  --config configs/inference.example.json \
  --allow-mock-backends \
  --validate-output-schema
```

---

## Validation

Run the main validation gate:

```bash
python scripts/phase19_check.py --stop-on-failure
```

Run individual checks:

```bash
python scripts/validate_assets.py
python scripts/check_runtime_deps.py
pytest -q
python scripts/jetson_health_check.py
```

The validation scripts are intentionally explicit so they can be reused in CI and deployment preflight checks.

---

## Runtime Modes

### Dry Run

Uses mock frame, telemetry, and detector backends.

```bash
PYTHONPATH=src python -m uas_ai_module.cli --dry-run --validate-output-schema
```

### Replay

Uses deterministic replay manifest data.

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --replay tests/fixtures/replay/sample_mission.json \
  --replay-steps 2 \
  --validate-output-schema
```

### Config-Built Runtime

Builds runtime components from a validated config.

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --run-once \
  --config configs/inference.example.json \
  --allow-mock-backends \
  --validate-output-schema
```

For real execution, remove `--allow-mock-backends` and provide real camera, telemetry, and model artifacts.

---

## Dataset Tooling

### Dataset Manifest Validation

```bash
python scripts/validate_dataset_manifest.py \
  configs/data/dataset_manifest.example.json \
  --dry-run
```

### Dataset Report

```bash
python scripts/generate_dataset_report.py \
  configs/data/dataset_manifest.example.json \
  --dry-run
```

### Class Balance Check

```bash
python scripts/check_class_balance.py \
  configs/data/dataset_manifest.example.json \
  --dry-run
```

### Dataset Converters

DOTA-style labels:

```bash
python scripts/convert_dota.py \
  tests/fixtures/converters/dota/labelTxt \
  --dry-run
```

VEDAI-style annotations:

```bash
python scripts/convert_vedai.py \
  tests/fixtures/converters/vedai/annotations.txt \
  --dry-run
```

xView-style GeoJSON:

```bash
python scripts/convert_xview.py \
  tests/fixtures/converters/xview/annotations.geojson \
  --dry-run
```

Merge common annotation JSON files:

```bash
python scripts/merge_annotations.py input_a.json input_b.json --dry-run
```

Export YOLO labels:

```bash
python scripts/export_yolo_dataset.py common_annotations.json --output-dir yolo_export
```

### X86 Training and Export Entry Points

These scripts are development-side only and support `--dry-run`.

```bash
python training/train_detector.py \
  --dataset-manifest configs/data/dataset_manifest.example.json \
  --epochs 1 \
  --dry-run

python training/export_onnx.py \
  --export-plan configs/models/export_plan.example.json \
  --dry-run

python training/build_tensorrt.py \
  --export-plan configs/models/export_plan.example.json \
  --dry-run
```

---

## Model Governance

Model governance is based on explicit manifests and metadata sidecars.

Example files:

```text
models/manifest.example.json
models/detector.metadata.example.json
configs/models/export_plan.example.json
```

Validate an export plan:

```bash
python scripts/prepare_model_export.py \
  configs/models/export_plan.example.json \
  --dry-run
```

Prepare model metadata:

```bash
python scripts/write_model_metadata.py \
  configs/models/export_plan.example.json \
  --dry-run
```

Validate ONNX metadata:

```bash
python scripts/onnx_runtime_smoke.py \
  models/detector.metadata.example.json \
  --dry-run
```

When real artifacts exist, verify hashes:

```bash
python scripts/onnx_runtime_smoke.py \
  models/detector.metadata.json \
  --verify-hash
```

---

## External Integration

External validation plan:

```text
configs/integration/external_validation.example.json
```

Dry-run the full plan:

```bash
python scripts/run_external_validation.py \
  configs/integration/external_validation.example.json \
  --dry-run
```

Run individual smoke checks:

```bash
python scripts/mavlink_smoke_test.py --dry-run
python scripts/camera_smoke_test.py --dry-run
python scripts/onnx_runtime_smoke.py models/detector.metadata.example.json --dry-run
python scripts/tensorrt_engine_check.py models/detector.engine --dry-run
python scripts/runtime_observability_smoke.py --dry-run --prometheus
```

Record read-only MAVLink telemetry when SITL or hardware is available:

```bash
python scripts/record_mavlink_telemetry.py \
  --endpoint udp:0.0.0.0:14550 \
  --samples 10 \
  --output reports/telemetry.jsonl
```

Capture camera frames when hardware is available:

```bash
python scripts/capture_camera_frames.py \
  --source 0 \
  --frames 5 \
  --output-dir reports/camera_frames
```

---

## Output Format

The advisory output schema is:

```text
schemas/output/advisory_v1_1.schema.json
```

Typical packet shape:

```json
{
  "schema_version": "1.1",
  "timestamp_utc": "...",
  "uas_id": "uas-dry-run",
  "advisory_only": true,
  "health": {
    "status": "ok",
    "warnings": [],
    "latency_ms": 0.0
  },
  "ownship": {
    "lat": 0.0,
    "lon": 0.0,
    "alt_msl_m": 0.0,
    "alt_agl_m": 0.0
  },
  "detections": [],
  "recommendations": []
}
```

Validate an output packet through the CLI:

```bash
PYTHONPATH=src python -m uas_ai_module.cli \
  --dry-run \
  --validate-output-schema
```

---

## Development Rules

1. Runtime code must remain advisory-only.
2. No vehicle command path should be added to the runtime.
3. Runtime dependencies must not include `torch`, `torchvision`, `torchaudio`, or `ultralytics`.
4. Runtime model artifacts must be `.onnx` or `.engine`.
5. Training checkpoints such as `.pt`, `.pth`, and `.ckpt` are allowed only in x86 training/export plans.
6. Heavy scripts must support `--dry-run`.
7. New config sections require JSON schemas.
8. Safety filters must remain hard-coded and non-configurable.
9. Any real hardware or model integration must include tests or smoke checks.
10. Validation gates should be updated when new top-level requirements are added.

---

## Known Limitations

The repository includes software scaffolding and validation tools for external integration, but the following require real external resources:

- PX4 or ArduPilot SITL endpoint
- physical camera source
- exported ONNX detector/classifier artifacts
- TensorRT engine and Jetson runtime
- DTED or equivalent terrain source
- real dataset downloads and annotations
- real model training runs
- hardware-backed metrics and thermal data

The project includes dry-run gates and smoke-test scripts for these areas, but it cannot complete physical validation without those resources.
