# Rebuild Plan – Most Required Phases First

Date: 2026-06-14

This rebuild intentionally focuses on the smallest useful, testable, safety-first core rather than trying to recreate all 12 previous phases at once.

## Scope boundary

The rebuilt system is an advisory-only UAS perception module for lawful monitoring, inspection, search, rescue, and operator decision support. It must not directly command a vehicle, weapon, or engagement action.

## Most required phases

### Rebuild Phase A – Safety-first runtime foundation

**Why required:** Everything else depends on correct config loading, module boundaries, and non-bypassable output safety filters.

Deliverables:

- Python package structure under `src/uas_ai_module/`
- Config loading and schema validation
- Semantic config validation for runtime safety
- Typed runtime dataclasses
- Advisory JSON serializer
- Hard-coded safety filters
- Unit tests for safety behavior

Acceptance criteria:

- Runtime inference config rejects `.pt` model artifacts.
- Output always includes `advisory_only: true`.
- Low-confidence detections are filtered.
- Civilian identifications are suppressed.
- Person detections below 30 m AGL are dropped.
- CEP above 25 m invalidates the advisory.

### Rebuild Phase B – Mocked end-to-end pipeline

**Why required:** We need a working executable pipeline before adding real engines/hardware.

Deliverables:

- Mock frame source
- Mock telemetry source
- Detector interface with mock detector
- Basic geolocation path
- Pipeline orchestrator
- CLI with `--dry-run`
- End-to-end tests

Acceptance criteria:

- `python -m uas_ai_module.cli --dry-run` emits valid advisory JSON.
- Pipeline can run without camera, MAVLink, TensorRT, or ONNX files.
- Failures are explicit and degrade safely.

### Rebuild Phase C – Runtime model integration boundary

**Why required:** Jetson runtime must never depend on PyTorch.

Deliverables:

- ONNX/TensorRT wrapper interfaces
- Artifact extension validation
- Model metadata validation
- Clear errors for unavailable runtime backends
- Runtime dependency guard

Acceptance criteria:

- `.onnx` and `.engine` are accepted by runtime wrappers.
- `.pt` is rejected by runtime wrappers.
- Backend import failures return actionable messages.

### Rebuild Phase D – Geolocation and prediction essentials

**Why required:** Advisory outputs need uncertainty-aware position information.

Deliverables:

- Basic pinhole ray-to-ground geolocation
- CEP estimate path
- Simple TCPA helper
- Track-state dataclasses
- Numerical tests

Acceptance criteria:

- Geolocation produces plausible lat/lon for down-looking camera geometry.
- Invalid calibration/telemetry fails closed.
- TCPA handles stationary, converging, and diverging cases.

### Rebuild Phase E – Integration tests and deployment scaffolding

**Why required:** Prevent regression before adding real cameras and models.

Deliverables:

- Safety regression suite
- Config schema tests
- Asset validation tests
- Example configs
- Basic systemd/deployment placeholders

Acceptance criteria:

- `pytest -q` passes.
- Validation scripts pass.
- Example config is accepted.

## Deferred until core is stable

These remain important, but should come after the core runtime is proven:

- Full data converters and training loops
- Real YOLO/EfficientNet training
- Online learning
- Multi-UAS mesh
- OTA server
- Ground station UI
- Federated learning
- Advanced robustness sweeps

## Current sprint target

Implement Rebuild Phases A and B first, with enough of C and D to establish safe boundaries.
