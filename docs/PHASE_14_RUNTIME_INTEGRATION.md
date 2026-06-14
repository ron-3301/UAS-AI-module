# Phase 14 — Runtime Integration Boundaries

Date: 2026-06-14

## Status

Phase 14 runtime integration boundary work is complete for the rebuilt baseline and passes the Phase 14 gate.

This phase does **not** yet claim real Jetson field readiness. It adds audited,
testable read-only integration boundaries for telemetry, camera ingestion,
runtime construction, and attitude-aware geolocation.

## Implemented

### Read-only MAVLink telemetry boundary

File:

```text
src/uas_ai_module/ingestion/mavlink.py
```

Features:

- receives MAVLink telemetry only
- parses `GLOBAL_POSITION_INT`
- parses `ATTITUDE`
- uses `VFR_HUD` heading as fallback
- converts MAVLink units into runtime `Telemetry`
- raises explicit errors on timeout or malformed global position
- does not send commands, missions, mode changes, actuator messages, or any autopilot control messages

### OpenCV camera ingestion boundary

File:

```text
src/uas_ai_module/ingestion/camera.py
```

Features:

- wraps OpenCV `VideoCapture`
- supports injected fake capture for tests
- validates image shape and NumPy array type
- emits runtime `Frame` objects
- fail-fast behavior when camera read fails

### Runtime factory helpers

File:

```text
src/uas_ai_module/runtime_factory.py
```

Features:

- builds detector by model artifact suffix
- builds frame source from config
- builds telemetry source from config
- preserves `.onnx` / `.engine` runtime boundaries
- supports mock construction for local tests

### Attitude-aware geolocation baseline

File:

```text
src/uas_ai_module/geolocation/attitude_raycaster.py
```

Features:

- local flat-ground pinhole projection with ownship attitude
- NED coordinate convention
- fail-closed behavior when ray does not intersect ground
- prepared for terrain/covariance hardening

## Tests added

```text
tests/test_phase14_ingestion_and_runtime_factory.py
tests/test_attitude_raycaster.py
```

Covered:

- MAVLink attitude + global position parsing
- MAVLink timeout behavior
- injected OpenCV camera source
- runtime factory mock sources
- attitude-aware center-pixel geolocation
- eastward movement for right-of-center pixel
- fail-closed ray miss behavior

## Current validation

```text
pytest: 69 passed
```

## Remaining work after Phase 14

1. Real local SITL MAVLink smoke test using pymavlink.
2. Real USB/CSI camera smoke test where hardware is available.
3. ONNX detector/classifier smoke tests with actual exported model sidecars.
4. TensorRT backend execution on Jetson.
5. Terrain/covariance geolocation hardening.
6. Prometheus/logging service integration.

## Safety note

The MAVLink integration remains strictly telemetry receive-only. No direct vehicle
control path has been added.
