# Phase 13 Implementation Audit

Date: 2026-06-14

## Executive summary

Phase 13 has started from the rebuilt baseline. The repository now has a coherent
safety-first runtime package with tests, schemas, replay, model metadata
validation, dependency guards, and deployment scaffolding.

The codebase is suitable for Phase 13 stabilization work. It is not yet a full
field-deployable Jetson system because real camera, MAVLink, TensorRT execution,
terrain-backed geolocation, and real model artifacts are intentionally left as
auditable integration boundaries.

## Audit scope

Audited areas:

- source package importability
- CLI/script contracts
- runtime vs development dependency split
- advisory-only safety behavior
- config and output schemas
- replay integration harness
- model manifest/metadata validation
- deployment scaffolding
- test coverage and validation commands

Out of scope for this audit pass:

- real Jetson TensorRT engine execution
- real MAVLink telemetry stream parsing
- real camera capture pipelines
- real model accuracy/latency benchmarking
- real terrain/DTED integration

## Repository health

| Area | Status | Notes |
|---|---:|---|
| Package imports | Pass | `tests/test_phase13_imports_and_cli_contracts.py` imports all runtime modules. |
| Asset validation | Pass | JSON/XML/schema validation via `scripts/validate_assets.py`. |
| Runtime dependency guard | Pass | PyTorch-family packages excluded from `requirements-runtime.txt`. |
| Unit/integration tests | Pass | Current baseline: `69 passed` after Phase 13 checks are added. |
| Dry-run CLI | Pass | Emits schema-valid advisory JSON. |
| Replay CLI | Pass | Emits schema-valid replay packets. |
| Output schema validation | Pass | Advisory packet validates against `advisory_v1_1`. |
| Script help contracts | Pass | Runtime scripts expose `--help`. |
| Heavy script dry-run | Pass | Replay script and Phase 13 gate expose `--dry-run`. |
| Deployment scaffold | Partial | systemd/logrotate/env examples exist; real production service still needs hardware config. |

## Safety audit

### Enforced behavior

The serializer enforces these hard-coded safety filters:

- detection confidence below `0.30` is dropped
- civilian identity confidence above `0.50` is suppressed
- person detections below `30 m AGL` are dropped
- CEP above `25 m` invalidates emitted detections
- stale telemetry invalidates emitted detections
- stale frame invalidates emitted detections
- recommendations are forced to `advisory_only: true`

### Advisory-only posture

The output schema and serializer both enforce advisory-only behavior. The current
codebase contains no MAVLink command transmitter, weapon command interface, or
autopilot command path.

### Remaining safety work

- Conduct formal safety review of output fields before external integration.
- Keep direct control/command interfaces out of runtime unless a separate human
  authorization and safety layer is specified.
- Add hardware-in-the-loop failure cases once real sensors are integrated.

## Dependency audit

Runtime dependencies are separated from development/training dependencies:

- `requirements/requirements-runtime.txt`
- `requirements/requirements-dev.txt`
- `requirements/requirements-uploaded.txt`

The uploaded combined requirements are preserved for traceability but should not
be used as the Jetson runtime install set.

## Schema audit

Schemas currently available:

- runtime config: `schemas/config/inference_runtime.schema.json`
- uploaded/general config: `schemas/config/inference.schema.json`
- output: `schemas/output/advisory_v1_1.schema.json`
- replay: `schemas/replay/mission_replay.schema.json`
- model manifest: `schemas/models/model_manifest.schema.json`
- model metadata: `schemas/models/model_metadata.schema.json`
- Phase 7-12 draft configs under `schemas/config/`

Runtime inference should use `inference_runtime.schema.json` because the uploaded
`inference.schema.json` still allows `.pt` structurally.

## Test audit

Current validation gate:

```bash
python scripts/phase13_check.py --stop-on-failure
```

This runs:

1. asset validation
2. runtime dependency guard
3. pytest suite
4. dry-run output schema validation
5. replay output schema validation
6. deployment health check

## Known limitations

| Limitation | Risk | Mitigation |
|---|---|---|
| TensorRT backend is a boundary only | No real Jetson engine execution yet | Implement on Jetson after Phase 13 review. |
| MAVLink backend is mock only | No real telemetry stream | Add real parser with stale/fail-closed behavior. |
| Geolocation is approximate | Lat/lon estimates are not production precision | Replace with attitude/terrain/covariance model. |
| Tracker is lightweight | Track IDs are basic | Replace/augment with Kalman/IMM tracker later. |
| ONNX decoder supports common layouts | Real models may require custom decoders | Use metadata and model-specific adapter tests. |

## Phase 13 stabilization recommendations

1. Keep `scripts/phase13_check.py` as the CI gate.
2. Treat `docs/module_status_matrix.md` as the living implementation tracker.
3. Freeze `advisory_v1_1` until deliberate schema versioning is needed.
4. Require tests for every new runtime backend.
5. Require all new config sections to include schemas and semantic validation.
6. Do not merge runtime dependencies that introduce PyTorch-family packages.
