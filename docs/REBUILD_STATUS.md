# Rebuild Status

Date: 2026-06-14

## Current focus

The rebuild is proceeding through the most required phases first:

1. Safety-first runtime foundation
2. Mocked end-to-end pipeline
3. Runtime model boundaries
4. Geolocation/TCPA essentials
5. Replay/integration harness
6. Deployment scaffolding
7. Phase 13 readiness documentation

## Implemented so far

### Runtime package

- `src/uas_ai_module/models.py` — core dataclasses for frames, telemetry, detections, geolocation, predictions, health, and pipeline results.
- `src/uas_ai_module/config.py` — JSON/YAML config loading, schema validation, and semantic runtime checks.
- `src/uas_ai_module/health.py` — staleness and degraded-health checks.
- `src/uas_ai_module/pipeline.py` — one-pass advisory pipeline orchestration.
- `src/uas_ai_module/cli.py` — dry-run and replay CLI with optional output-schema validation.
- `src/uas_ai_module/model_manifest.py` — runtime model manifest validation.
- `src/uas_ai_module/model_metadata.py` — model sidecar metadata and hash validation.

### Ingestion

- `ingestion/frame_capture.py` — `FrameSource` protocol and deterministic `MockFrameSource`.
- `ingestion/telemetry_parser.py` — `TelemetrySource` protocol and deterministic `MockTelemetrySource`.
- `ingestion/replay.py` — deterministic mission replay dataset, frame source, and telemetry source.
- `ingestion/file_source.py` — local `.npy` image and optional OpenCV image/video frame ingestion.

### Detection

- `detection/detector.py` — detector protocol, mock detector, runtime artifact validation.
- `detection/nms.py` — IoU, clipping, and greedy NMS.
- `detection/onnx_detector.py` — ONNX detector wrapper with injectable session for tests.
- `detection/tensorrt_detector.py` — TensorRT `.engine` boundary with clear unsupported-backend error until Jetson implementation.

Runtime model rules:

- `.onnx` accepted by ONNX detector.
- `.engine` accepted by TensorRT detector boundary.
- `.pt` and `.pth` rejected in runtime paths.

### Identification

- `identification/classifier.py` — mock classifier and ONNX classifier boundary.
- `identification/crop_extractor.py` — strict image crop extraction with clipping.
- Pipeline can apply classifier output to detections before safety serialization.

### Geolocation and prediction

- `geolocation/raycaster.py` — basic pinhole ray-to-ground estimate with fail-closed invalid states.
- `prediction/tcpa.py` — 2D TCPA helper.

### Output

- `output/json_serializer.py` — versioned advisory packet serializer with hard-coded safety filters.
- `output/schema_validator.py` — validates advisory packets against `schemas/output/advisory_v1_1.schema.json`.

Hard-coded safety behavior:

- Detection confidence below `0.30` is dropped.
- Civilian identification above ID confidence `0.50` is suppressed.
- Person detections below `30 m AGL` are dropped.
- CEP above `25 m` invalidates the emitted detection.
- Stale telemetry/frame warnings invalidate emitted detections.
- Output always includes `advisory_only: true`.

### Replay/integration harness

- `tests/fixtures/replay/sample_mission.json` — deterministic two-frame replay fixture.
- `schemas/replay/mission_replay.schema.json` — replay manifest schema.
- `scripts/replay_mission.py` — CLI replay runner.
- `uas_ai_module.cli --replay ...` — built-in replay mode.

### Model governance foundation

- `schemas/models/model_manifest.schema.json` — runtime model manifest schema.
- `schemas/models/model_metadata.schema.json` — model sidecar metadata schema.
- `models/manifest.example.json` — example model manifest.
- `src/uas_ai_module/model_manifest.py` — manifest loader, semantic validator, and optional artifact hash checker.
- `src/uas_ai_module/model_metadata.py` — metadata sidecar loader and SHA-256 verifier.

### Deployment scaffolding

- `deploy/systemd/uas-ai-module.service` — baseline systemd unit.
- `deploy/systemd/uas-ai-module.env.example` — environment-file example.
- `deploy/logrotate/uas-ai-module` — log rotation example.
- `docs/deployment_quickstart.md` — deployment scaffold notes.
- `scripts/jetson_health_check.py` — runtime dependency and dry-run advisory health check.

## Tests

Current test result:

```text
69 passed
```

Test coverage areas:

- asset parsing
- runtime dependency guard
- config validation and `.pt` rejection
- output safety filters
- advisory output schema validation
- mocked end-to-end pipeline
- CLI dry run
- deterministic replay mode and replay CLI
- model manifest validation and model metadata hash verification
- geolocation fail-closed behavior
- TCPA converging/diverging cases
- NMS and ONNX detector output decoding
- classifier wrapper and crop extraction
- stale telemetry/frame invalidation
- deployment health-check script

## Validation commands

From repo root:

```bash
python scripts/validate_assets.py
python scripts/check_runtime_deps.py
pytest -q
PYTHONPATH=src python -m uas_ai_module.cli --dry-run --validate-output-schema --pretty
PYTHONPATH=src python -m uas_ai_module.cli --replay tests/fixtures/replay/sample_mission.json --replay-steps 2 --validate-output-schema
python scripts/jetson_health_check.py
```

## Still required before saying the rebuild is totally finished

The rebuild is close to a complete core baseline, but it is **not totally finished** yet. Before declaring the project ready for Phase 13 audit/stabilization, complete these remaining rebuild items:

### 1. Geolocation hardening

Replace the basic flat-ground approximation with attitude-aware calibrated projection and terrain hooks.

### 2. Track lifecycle basics

Add a lightweight tracker/track-state manager so detections have stable local track IDs across replay frames.

### 3. Runtime backend adapter polish

Add model metadata cross-checks inside ONNX detector/classifier construction, including expected input/output names and class-map validation.

### 4. Safety-contract final pass

Add explicit tests for invalid calibration handling and output schema compatibility across versions.

### 5. Packaging finalization

Add a release checklist, generated project tree, and final rebuild-complete report.

## Recommended next rebuild pass

Next pass should implement:

1. lightweight track manager
2. attitude-aware geolocation helpers
3. metadata-aware ONNX wrapper construction
4. final safety/report docs

## Phase 13 readiness

The safety-first core rebuild is now complete enough to enter Phase 13 audit/stabilization. See `docs/PHASE_13_READINESS.md`.
