# Phase 17 — External SITL / Hardware Execution Readiness

Date: 2026-06-14

## Status

Phase 17 external execution readiness is complete for this workspace.

This phase adds advisory-only external validation planning and dry-run gates for
resources that must be supplied outside the sandbox: SITL MAVLink, real camera,
real ONNX artifacts, TensorRT engines, and runtime observability capture.

## Implemented

### External validation plan and report schemas

```text
schemas/integration/external_validation_plan.schema.json
schemas/integration/external_validation_report.schema.json
configs/integration/external_validation.example.json
```

The plan schema requires:

```json
"advisory_only": true
```

### External validation runner

```text
scripts/run_external_validation.py
```

Supports:

- MAVLink smoke check
- camera smoke check
- ONNX Runtime smoke check
- TensorRT boundary check
- observability smoke check
- dry-run planning mode
- JSON report output

### Read-only telemetry/camera capture helpers

```text
scripts/record_mavlink_telemetry.py
scripts/capture_camera_frames.py
```

Both support `--dry-run`.

### Phase 17 gate

```text
scripts/phase17_check.py
```

Runs:

1. Phase 16 gate
2. external validation plan dry-run
3. MAVLink telemetry recorder dry-run
4. camera capture dry-run

## Validation

Command:

```bash
python scripts/phase17_check.py --stop-on-failure
```

Result:

```text
Phase 17 external execution readiness check passed
pytest: 91 passed
```

## Safety posture

- MAVLink validation remains read-only.
- No command sender was added.
- No mission upload path was added.
- No vehicle control path was added.
- External validation plan requires `advisory_only: true`.

## How to run real external checks later

With external resources connected:

```bash
python scripts/run_external_validation.py configs/integration/external_validation.example.json --output reports/external_validation_report.json
```

Or individual checks:

```bash
python scripts/mavlink_smoke_test.py --endpoint udp:0.0.0.0:14550
python scripts/record_mavlink_telemetry.py --endpoint udp:0.0.0.0:14550 --samples 10 --output reports/telemetry.jsonl
python scripts/camera_smoke_test.py --source 0 --frames 5
python scripts/capture_camera_frames.py --source 0 --frames 5 --output-dir reports/camera_frames
python scripts/onnx_runtime_smoke.py models/detector.metadata.json --verify-hash
python scripts/tensorrt_engine_check.py models/detector.engine
python scripts/runtime_observability_smoke.py --log-jsonl reports/advisory.jsonl --prometheus
```

## Remaining work after Phase 17

The next tasks require actual external resources:

1. Run the validation plan against SITL.
2. Run camera validation on target hardware.
3. Run ONNX validation against real exported models.
4. Implement actual TensorRT inference on Jetson.
5. Collect and archive validation reports.
