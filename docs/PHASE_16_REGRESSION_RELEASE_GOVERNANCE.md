# Phase 16 — Regression & Release Governance

Date: 2026-06-14

## Status

Phase 16 regression/release governance is complete for the rebuilt baseline.

This phase adds deterministic replay regression, source release manifesting, and
a minimal requirements-based SBOM so the project can be packaged and audited more
safely before real hardware/model integration.

## Implemented

### Golden replay regression

Files:

```text
src/uas_ai_module/output/golden.py
scripts/generate_golden_replay.py
tests/fixtures/replay/sample_mission.golden.json
```

Features:

- normalized advisory packets for stable regression comparison
- volatile field normalization for timestamp, latency, staleness, temperature,
  and power
- golden replay generation
- golden replay comparison

### Source release manifest

Files:

```text
src/uas_ai_module/release/source_manifest.py
scripts/build_release_manifest.py
schemas/release/source_manifest.schema.json
```

Features:

- SHA-256 per source file
- file size tracking
- excluded transient/build/cache paths
- dry-run summary mode

### Minimal SBOM

Files:

```text
src/uas_ai_module/release/sbom.py
scripts/generate_sbom.py
schemas/release/sbom.schema.json
```

Features:

- parses requirements files
- records package name, specifier, environment marker, and source file
- dry-run summary mode

### Phase 16 gate

File:

```text
scripts/phase16_check.py
```

Runs:

1. Phase 15 gate
2. golden replay comparison
3. source release manifest dry-run
4. SBOM dry-run

## Validation

Command:

```bash
python scripts/phase16_check.py --stop-on-failure
```

Result:

```text
Phase 16 regression/release governance check passed
pytest: 91 passed
```

## Safety posture

This phase does not add runtime control behavior. It only adds regression and
release-governance tooling around the existing advisory-only runtime.

## Recommended next phase

Proceed to Phase 17: actual external integration execution when resources are
available:

1. Run `scripts/mavlink_smoke_test.py` against SITL.
2. Run `scripts/camera_smoke_test.py` against real camera source.
3. Run `scripts/onnx_runtime_smoke.py` against real exported model metadata.
4. Run TensorRT backend implementation and engine smoke on Jetson.
5. Generate a source release manifest and SBOM for release artifacts.
