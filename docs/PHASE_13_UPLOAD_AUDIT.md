# Phase 13 Upload Audit

Date: 2026-06-14

This audit reflects only the files currently available in the Arena workspace. The main source tree from the original project has not yet been uploaded, so implementation claims from the Phase 1–12 summary cannot be verified at module level yet.

## Files received

| File | Current location | Notes |
|---|---|---|
| `PROJECT_SUMMARY_PHASES_1-12.md` | `docs/PROJECT_SUMMARY_PHASES_1-12.md` | Main continuity document. Describes Phases 1–12 and future gaps. |
| `README.md` | `README.uploaded.md` | Very short status README; preserved exactly. |
| `CHANGELOG.md` | `CHANGELOG.md` | Dataset changelog placeholder. |
| `SOP_rulings.md` | `docs/SOP_rulings.md` | Annotation edge-case rulings. |
| `requirements.txt` | `requirements/requirements-uploaded.txt` | Combined dev/runtime requirements; preserved for traceability. |
| `inference.schema.json` | `schemas/config/inference.schema.json` | Uploaded schema; parses successfully. See concerns below. |
| `training.schema.json` | `schemas/config/training.schema.json` | Uploaded schema; parses successfully. |
| `class_weights.schema.json` | `schemas/config/class_weights.schema.json` | Uploaded schema; parses successfully. |
| `cam01_intrinsics.schema.json` | `schemas/config/cam01_intrinsics.schema.json` | Uploaded schema; parses successfully. |
| `airsim_waypoints.json` | `sim/airsim_waypoints.json` | Valid JSON waypoint fixture. |
| `label_studio_project.xml` | `labeling/label_studio_project.xml` | Valid XML Label Studio config. |
| `mosquitto.conf` | `deploy/mosquitto/mosquitto.conf` | MQTT broker config with anonymous access disabled. |

## Validation performed

The following local parse checks passed:

- JSON parse for all uploaded JSON and JSON-schema files.
- XML parse for `label_studio_project.xml`.
- Structural organization into a repo-like layout.

Run:

```bash
python scripts/validate_assets.py
python scripts/check_runtime_deps.py
pytest -q
```

## Important findings

### 1. Source code is missing

The summary references many source files, for example:

- `src/pipeline.py`
- `src/output/json_serializer.py`
- `src/geolocation/imm_kalman.py`
- `src/coordination/mesh_comm.py`
- `scripts/benchmark_latency.py`
- `training/train_detector.py`

Those files are not present in the current upload. Until they are provided, we cannot verify whether the implementation is complete, stubbed, broken, or production-ready.

### 2. Runtime/development dependencies were mixed

The uploaded `requirements.txt` includes both runtime and x86 training/development packages:

- Runtime-relevant packages: `onnxruntime`, `opencv-python-headless`, `numpy`, `scipy`, `pymavlink`, `pyzmq`, `paho-mqtt`, `prometheus-client`, etc.
- Training/development packages: `torch`, `torchvision`, `ultralytics`, `dvc`, `mlflow`, `pytest`, `ruff`, `mypy`.

This conflicts with the stated Jetson rule that PyTorch packages must not be runtime dependencies. I therefore split dependencies into:

- `requirements/requirements-runtime.txt`
- `requirements/requirements-dev.txt`
- `requirements/requirements-uploaded.txt` for traceability

### 3. Inference schema allows `.pt` weights

The uploaded `inference.schema.json` permits:

```json
"pattern": "\\.(pt|onnx|engine)$"
```

For the Jetson runtime, `.pt` should not be accepted. The runtime should accept `.onnx` and `.engine` only. If `.pt` is needed anywhere, it should be restricted to x86 training/export configs, not inference deployment.

Recommended action:

- Create a hardened runtime schema version that rejects `.pt`.
- Keep `.pt` support only in training/export schemas.

### 4. Uploaded schemas are permissive by default

The uploaded schemas generally do not include `additionalProperties: false`, so unknown config fields would be accepted by default. That can hide typos and make safety review harder.

Recommended action:

- Move toward strict schemas for runtime configs.
- Use explicit extension points only where required.

### 5. Cross-field validation is not represented

Some important constraints are hard or impossible to express in Draft-07 JSON Schema alone, for example:

- Dataset split fractions should sum to 1.0.
- `dted_path` should be required when `terrain_model` is `dted1` or `dted2`.
- If telemetry source is `file`, a file path should be required.
- Runtime model artifact should match runtime backend.

Recommended action:

- Keep JSON Schema for structural validation.
- Add Python-level semantic validators in `src/config.py` or equivalent.

### 6. Advisory-only behavior should be encoded everywhere

The Phase 1–12 summary repeatedly states advisory-only behavior. That should be enforced in:

- output schemas
- autonomy config schemas
- integration tests
- docs/safety contract
- code-level interfaces

The drafted `schemas/output/advisory_v1_1.schema.json` and `schemas/config/autonomy.schema.json` encode `advisory_only: true` as a constant.

## New files created during continuation

| File | Purpose |
|---|---|
| `README.md` | Continuation README explaining current state. |
| `.gitignore` | Baseline project ignore rules. |
| `requirements/requirements-runtime.txt` | Jetson-safe runtime requirements. |
| `requirements/requirements-dev.txt` | x86 development/training requirements. |
| `docs/UNSUPPORTED_FILE_TRANSFER.md` | How to provide unsupported files. |
| `docs/PHASE_13_UPLOAD_AUDIT.md` | This audit. |
| `schemas/config/adaptation.schema.json` | Draft config schema for Phase 7. |
| `schemas/config/coordination.schema.json` | Draft config schema for Phase 8. |
| `schemas/config/prediction.schema.json` | Draft config schema for Phase 9. |
| `schemas/config/autonomy.schema.json` | Draft config schema for Phase 10. |
| `schemas/config/robustness.schema.json` | Draft config schema for Phase 11. |
| `schemas/config/fusion.schema.json` | Draft config schema for thermal/EO fusion. |
| `schemas/config/updater.schema.json` | Draft config schema for Phase 12 OTA. |
| `schemas/config/metrics.schema.json` | Draft config schema for Prometheus/runtime metrics. |
| `schemas/config/fleet_logging.schema.json` | Draft config schema for log aggregation. |
| `schemas/output/advisory_v1_1.schema.json` | Draft output schema for advisory JSON. |
| `scripts/validate_assets.py` | Local asset/schema validation. |
| `scripts/check_runtime_deps.py` | Guards against forbidden runtime dependencies. |
| `tests/test_assets.py` | Baseline pytest checks for available assets. |

## Recommended next actions

1. Upload the actual source tree or a ZIP/TAR archive if possible.
2. If archives are unsupported, follow `docs/UNSUPPORTED_FILE_TRANSFER.md`.
3. Merge the schema and dependency split into the original repo.
4. Run a full module import test once `src/` is available.
5. Add safety regression tests around `src/output/json_serializer.py`.
6. Harden `inference.schema.json` for runtime deployment by rejecting `.pt`.
7. Continue Phase 13 before implementing new capabilities.
