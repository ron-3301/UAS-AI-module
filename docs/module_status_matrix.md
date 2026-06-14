# Module Status Matrix

Date: 2026-06-14

Legend:

- **Complete baseline**: implemented, tested, and suitable as Phase 13 baseline.
- **Boundary**: validates contracts but awaits real hardware/model integration.
- **Partial**: useful implementation exists but needs production hardening.
- **Deferred**: intentionally not rebuilt yet.

| Module/File | Status | Test Coverage | Notes / Next Action |
|---|---|---|---|
| `src/uas_ai_module/models.py` | Complete baseline | dataclass usage throughout tests | Core runtime dataclasses. |
| `src/uas_ai_module/config.py` | Complete baseline | config/runtime schema tests | Add more semantic validators as configs grow. |
| `src/uas_ai_module/cli.py` | Complete baseline | dry-run/replay/help tests | Real runtime backend flags can be added later. |
| `src/uas_ai_module/pipeline.py` | Complete baseline | pipeline/replay/classification tests | Orchestrates rebuilt core. |
| `runtime_factory.py` | Complete baseline | factory and CLI run-once tests | Runtime component construction helpers; real backend execution depends on artifacts/hardware. |
| `src/uas_ai_module/health.py` | Complete baseline | stale telemetry/frame tests | Add hardware collectors later. |
| `src/uas_ai_module/model_manifest.py` | Complete baseline | manifest/hash tests | Integrate with deployment once real artifacts exist. |
| `src/uas_ai_module/model_metadata.py` | Complete baseline | metadata/hash tests | Use for real ONNX/TensorRT artifact checks. |
| `ingestion/frame_capture.py` | Complete baseline | dry-run tests | Mock source only. |
| `ingestion/telemetry_parser.py` | Complete baseline | dry-run/stale tests | Mock source only. |
| `ingestion/replay.py` | Complete baseline | replay tests | Deterministic replay harness. |
| `ingestion/file_source.py` | Partial | `.npy` image source tests | OpenCV image/video path needs hardware/local validation. |
| `ingestion/mavlink.py` | Boundary | fake MAVLink connection tests | Read-only telemetry parsing; SITL/hardware validation still needed. |
| `ingestion/camera.py` | Boundary | camera injected-capture tests | Real OpenCV camera source; hardware validation still needed. |
| `detection/detector.py` | Complete baseline | runtime boundary tests | Protocol, mock detector, artifact validation. |
| `detection/nms.py` | Complete baseline | NMS/IoU tests | Greedy NMS baseline. |
| `detection/onnx_detector.py` | Partial | fake-session decoder tests | Needs real exported model smoke tests. |
| `detection/tensorrt_detector.py` | Boundary | suffix validation tests | Implement on Jetson with TensorRT. |
| `identification/classifier.py` | Partial | fake-session classifier tests | Needs real exported model smoke tests. |
| `identification/crop_extractor.py` | Complete baseline | crop tests | Strict crop extraction. |
| `geolocation/raycaster.py` | Partial | geolocation tests | Replace with attitude/terrain/covariance hardening. |
| `geolocation/attitude_raycaster.py` | Partial | attitude geolocation tests | Attitude-aware flat-ground projection; terrain/covariance still needed. |
| `geolocation/transforms.py` | Complete baseline | transform tests | Utility helpers. |
| `prediction/tcpa.py` | Complete baseline | TCPA tests | Expand to covariance-aware TCPA later. |
| `tracking/track_manager.py` | Partial | stable ID/expiry tests | Lightweight tracker, not IMM/Kalman. |
| `output/json_serializer.py` | Complete baseline | safety regression tests | Hard-coded filters must stay non-configurable. |
| `output/schema_validator.py` | Complete baseline | output schema tests | Schema validation for packets. |
| `scripts/validate_assets.py` | Complete baseline | help/phase13 gate | Asset/schema validation. |
| `scripts/check_runtime_deps.py` | Complete baseline | help/phase13 gate | Runtime dependency guard. |
| `scripts/replay_mission.py` | Complete baseline | replay/help/dry-run tests | Deterministic replay runner. |
| `scripts/jetson_health_check.py` | Complete baseline | health-check test | Conservative deployment check. |
| `scripts/phase13_check.py` | Complete baseline | help/dry-run test | CI/stabilization gate. |
| `deploy/systemd/uas-ai-module.service` | Boundary | asset presence only | Needs device-specific config before production. |
| `deploy/logrotate/uas-ai-module` | Complete baseline | asset presence | Log rotation example. |
| Multi-UAS coordination | Deferred | none | Rebuild after core/hardware baseline. |
| OTA updater | Deferred | none | Rebuild after runtime deployment story matures. |
| Ground station GUI | Deferred | none | Productization phase. |
| Training/data pipeline | Deferred | none | x86-only rebuild after runtime audit. |
