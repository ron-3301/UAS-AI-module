# Phase 13 Readiness Report

Date: 2026-06-14

## Verdict

The safety-first core rebuild is complete enough to enter **Phase 13: Repository Reality Audit & Stabilization**.

This does **not** mean the full original 12-phase production system is complete. It means the reconstructed codebase now has a coherent, testable, advisory-only runtime baseline that Phase 13 can audit, stabilize, and extend.

## Validation status

Latest checks:

```text
python scripts/validate_assets.py        PASS
python scripts/check_runtime_deps.py     PASS
python scripts/jetson_health_check.py    PASS
pytest -q                               69 passed
CLI dry-run schema validation            PASS
CLI replay schema validation             PASS
```

## Core guarantees currently enforced

- Runtime dependency guard keeps PyTorch/Ultralytics out of Jetson runtime requirements.
- Runtime model paths reject `.pt` and `.pth` artifacts.
- Strict runtime inference schema rejects `.pt` structurally.
- Advisory output always carries `advisory_only: true`.
- Output packets validate against `schemas/output/advisory_v1_1.schema.json`.
- Safety filters are hard-coded in code, not config:
  - detection confidence below `0.30` is dropped
  - civilian identity confidence above `0.50` is suppressed
  - person detections below `30 m AGL` are dropped
  - CEP above `25 m` invalidates emitted detections
  - stale telemetry/frame invalidates emitted detections
- Replay mode provides deterministic integration coverage.
- Model manifest and metadata sidecar validation exist, including SHA-256 checks.
- Deployment scaffolding exists for systemd, environment file, log rotation, and health check.

## Implemented rebuild modules

```text
src/uas_ai_module/
  cli.py
  config.py
  health.py
  model_manifest.py
  model_metadata.py
  models.py
  pipeline.py
  detection/
  geolocation/
  identification/
  ingestion/
  output/
  prediction/
  tracking/
```

## Implemented validation/test areas

- asset parsing
- config validation
- strict runtime schema validation
- runtime dependency guard
- dry-run CLI
- replay CLI
- advisory output schema validation
- output safety regression tests
- stale frame/telemetry invalidation
- NMS and ONNX detector output decoding
- TensorRT artifact boundary
- ONNX classifier wrapper
- crop extraction
- model manifest validation
- model metadata/hash validation
- local track manager
- geolocation helper transforms
- deployment health-check script

## Phase 13 entry criteria

The rebuilt codebase now satisfies the entry criteria for Phase 13:

1. The package imports successfully.
2. The core pipeline runs end-to-end in dry-run mode.
3. The replay harness runs deterministically.
4. Safety filters have regression tests.
5. Output schema validation is implemented.
6. Runtime dependency boundaries are enforced.
7. Runtime model artifact boundaries are enforced.
8. Deployment scaffolding exists.
9. Tests pass.

## What Phase 13 should do next

Phase 13 should now audit and stabilize this rebuilt baseline:

1. Confirm every source module has a clear owner and purpose.
2. Freeze the current advisory output schema as baseline `1.1`.
3. Add CI automation around the validation commands.
4. Review safety filters and failure modes.
5. Review runtime/development dependency separation.
6. Decide whether to keep, replace, or expand each rebuilt placeholder boundary.
7. Start replacing boundaries with real hardware/model integrations only after audit.

## Known limitations entering Phase 13

- Real TensorRT engine execution is not implemented in this environment.
- Real MAVLink ingestion is not implemented yet.
- Real camera/video ingestion exists only as local file/video scaffolding.
- The geolocation model is still a conservative flat-ground approximation with helper transforms prepared for hardening.
- The tracker is lightweight and deterministic, not a full Kalman/IMM tracker.
- The ONNX wrappers support common output formats but still need model-specific metadata testing with real exported models.

## Recommendation

Proceed to Phase 13 now. Treat this rebuild as the new baseline and use Phase 13 to perform a formal repository audit, CI setup, safety review, and module-by-module stabilization before moving into real model/hardware integration.
