# uas-ai-module — continuation workspace

This workspace is a reconstructed continuation package based on the files uploaded in Arena plus the Phase 1–12 project summary.

## What is available here

Uploaded/reference files have been organized into a conventional project layout:

- `docs/PROJECT_SUMMARY_PHASES_1-12.md` — source summary of phases already described
- `docs/FUTURE_PHASE_PLAN_13_PLUS.md` — future roadmap drafted from the summary
- `docs/REBUILD_MOST_REQUIRED_PHASES.md` — focused rebuild plan for the required core
- `docs/REBUILD_STATUS.md` — current implemented rebuild status and next tasks
- `docs/PHASE_13_READINESS.md` — readiness report for Phase 13 audit/stabilization
- `docs/PHASE_13_COMPLETION_REPORT.md` — completed Phase 13 audit/stabilization report
- `docs/PHASE_14_RUNTIME_INTEGRATION.md` — runtime integration boundary work
- `docs/PHASE_14_COMPLETION_REPORT.md` — completed Phase 14 report
- `docs/implementation_audit.md` — Phase 13 implementation audit
- `docs/module_status_matrix.md` — module-by-module status matrix
- `docs/RELEASE_CHECKLIST.md` — baseline validation checklist
- `docs/PHASE_13_UPLOAD_AUDIT.md` — audit of the initially uploaded files
- `src/uas_ai_module/` — rebuilt safety-first runtime core
- `configs/` — example runtime and camera calibration configs
- `schemas/config/` — config schemas, including uploaded schemas and newly drafted Phase 7–12 schemas
- `schemas/output/` — drafted advisory output schema
- `sim/airsim_waypoints.json` — uploaded AirSim waypoint fixture
- `labeling/label_studio_project.xml` — uploaded Label Studio config
- `deploy/mosquitto/mosquitto.conf` — uploaded MQTT broker config
- `requirements/` — separated runtime/dev dependency files
- `scripts/` — validation and dependency guard scripts
- `tests/` — asset, config, pipeline, geolocation, TCPA, and safety regression tests

## Key continuation rule

The original Python source tree was not uploaded. This workspace therefore contains a rebuilt safety-first runtime baseline plus Phase 13 audit/stabilization scaffolding. If the original repository later becomes available, merge it carefully and update `docs/implementation_audit.md` and `docs/module_status_matrix.md` with a new module-level reality check.

## Non-negotiable runtime constraints

- Jetson runtime: TensorRT + ONNX Runtime only for inference.
- No PyTorch/torchvision/torchaudio on Jetson runtime.
- Heavy scripts must support `--dry-run`.
- Hard-coded safety filters remain non-configurable.
- New YAML config sections require JSON schemas.
- The system remains advisory-only; generated recommendations must not directly command a vehicle or weapon system.

## Quick checks

From this directory:

```bash
python scripts/validate_assets.py
python scripts/check_runtime_deps.py
pytest -q
PYTHONPATH=src python -m uas_ai_module.cli --dry-run --validate-output-schema --pretty
PYTHONPATH=src python -m uas_ai_module.cli --replay tests/fixtures/replay/sample_mission.json --replay-steps 2 --validate-output-schema
python scripts/jetson_health_check.py
python scripts/phase13_check.py --stop-on-failure
python scripts/phase14_check.py --stop-on-failure
```

If `jsonschema` is installed, `validate_assets.py` also runs Draft-07 schema checks.

## Dependency files

- `requirements/requirements-runtime.txt` — Jetson/runtime dependencies only; forbidden PyTorch packages excluded.
- `requirements/requirements-dev.txt` — x86 development/training dependencies, including training-only PyTorch/Ultralytics.
- `requirements/requirements-uploaded.txt` — the original uploaded combined requirement file, preserved for traceability.

## Next step

Upload the rest of the source repository as a ZIP/TAR archive if possible, or see `docs/UNSUPPORTED_FILE_TRANSFER.md` for alternatives.
