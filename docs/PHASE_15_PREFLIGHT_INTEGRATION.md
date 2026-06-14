# Phase 15 — SITL / Hardware / Model Artifact Preflight Integration

Date: 2026-06-14

## Status

Phase 15 preflight integration is complete for the rebuilt baseline.

This phase adds executable preflight checks and runtime hooks for real SITL,
camera, model artifact, TensorRT-boundary, terrain, and observability work. It
cannot certify physical hardware or real exported model accuracy inside this
workspace because no SITL instance, Jetson, camera, or model artifacts are
attached.

## Implemented

### Terrain-aware geolocation hooks

Files:

```text
src/uas_ai_module/geolocation/terrain.py
src/uas_ai_module/geolocation/attitude_raycaster.py
```

Implemented:

- `TerrainProvider` protocol
- `FlatTerrainProvider`
- `GridTerrainProvider`
- JSON terrain loader
- iterative flat-earth terrain intersection hook in attitude-aware raycaster
- fail-closed handling for ownship below terrain

### Runtime observability baseline

Files:

```text
src/uas_ai_module/metrics/runtime_metrics.py
src/uas_ai_module/output/jsonl_logger.py
scripts/runtime_observability_smoke.py
```

Implemented:

- metric snapshot extraction from advisory packets
- Prometheus text-format rendering without mandatory prometheus dependency
- append-only JSONL advisory logging
- observability smoke script

### ONNX runtime preflight smoke

File:

```text
scripts/onnx_runtime_smoke.py
```

Implemented:

- metadata sidecar validation in dry-run mode
- optional real ONNX Runtime session opening when artifact/runtime are available
- input/output name comparison against model metadata

### Phase 15 gate

File:

```text
scripts/phase15_check.py
```

Runs:

1. Phase 14 gate
2. ONNX runtime smoke dry-run
3. observability smoke dry-run

## Validation

Command:

```bash
python scripts/phase15_check.py --stop-on-failure
```

Result:

```text
Phase 15 preflight check passed
pytest: 91 passed
```

## Safety posture

- No MAVLink command sender added.
- No vehicle control path added.
- No weapon/engagement logic added.
- Advisory-only JSON behavior remains enforced.
- Runtime `.pt` / `.pth` rejection remains enforced.

## What still requires external hardware/artifacts

These are now ready to run when resources exist, but they cannot be completed in
this workspace:

1. SITL MAVLink smoke test against PX4/ArduPilot.
2. Real USB/CSI camera smoke test.
3. Real ONNX detector/classifier session smoke with exported artifacts.
4. Real TensorRT engine execution on Jetson.
5. Terrain provider backed by DTED/real elevation data.
6. Hardware-backed Prometheus metrics.

## Recommended next step

Proceed to hardware/model artifact validation using the smoke scripts:

```bash
python scripts/mavlink_smoke_test.py --endpoint udp:0.0.0.0:14550
python scripts/camera_smoke_test.py --source 0 --frames 5
python scripts/onnx_runtime_smoke.py models/detector.metadata.json --verify-hash
python scripts/tensorrt_engine_check.py models/detector.engine
python scripts/runtime_observability_smoke.py --log-jsonl logs/advisory.jsonl --prometheus
```
