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

| `geolocation/terrain.py` | Complete baseline | terrain provider tests | Flat/grid terrain hooks; DTED provider pending. |
| `metrics/runtime_metrics.py` | Complete baseline | metrics/prometheus tests | Dependency-free metric extraction and text rendering. |
| `output/jsonl_logger.py` | Complete baseline | JSONL round-trip tests | Append-only local advisory logging. |
| `scripts/onnx_runtime_smoke.py` | Complete baseline | dry-run/help tests | Optional real ONNX Runtime session smoke when artifact exists. |
| `scripts/runtime_observability_smoke.py` | Complete baseline | dry-run/logging tests | Observability preflight. |
| `scripts/phase15_check.py` | Complete baseline | dry-run/gate run | Phase 15 preflight gate. |
| `output/golden.py` | Complete baseline | golden replay tests | Normalizes advisory packets for deterministic regression. |
| `release/source_manifest.py` | Complete baseline | release manifest tests | SHA-256 source manifest generation. |
| `release/sbom.py` | Complete baseline | SBOM parser tests | Requirements-based SBOM baseline. |
| `scripts/generate_golden_replay.py` | Complete baseline | compare/dry-run tests | Golden replay generation/comparison. |
| `scripts/build_release_manifest.py` | Complete baseline | dry-run tests | Source release manifest generation. |
| `scripts/generate_sbom.py` | Complete baseline | dry-run tests | Requirements SBOM generation. |
| `scripts/phase16_check.py` | Complete baseline | phase16 gate | Regression/release-governance gate. |
| `integration/external_validation.py` | Complete baseline | plan parser tests | Advisory-only external validation plan loader. |
| `scripts/run_external_validation.py` | Complete baseline | dry-run report tests | External SITL/hardware validation runner. |
| `scripts/record_mavlink_telemetry.py` | Complete baseline | dry-run tests | Read-only MAVLink telemetry recorder. |
| `scripts/capture_camera_frames.py` | Complete baseline | dry-run tests | Camera frame capture helper. |
| `scripts/phase17_check.py` | Complete baseline | phase17 gate | External execution readiness gate. |
| `data/dataset_manifest.py` | Complete baseline | dataset manifest/report/class-balance tests | Dataset governance metadata loader. |
| `data/export_plan.py` | Complete baseline | export plan tests | X86/export artifact governance. |
| `scripts/validate_dataset_manifest.py` | Complete baseline | dry-run tests | Dataset manifest validator. |
| `scripts/generate_dataset_report.py` | Complete baseline | dry-run tests | Dataset report generator. |
| `scripts/check_class_balance.py` | Complete baseline | dry-run tests | Dataset class-balance checker. |
| `scripts/prepare_model_export.py` | Complete baseline | dry-run tests | Export-plan validator/preparer. |
| `scripts/write_model_metadata.py` | Complete baseline | dry-run tests | Metadata sidecar writer. |
| `training/train_detector.py` | Boundary | dry-run/help tests | X86-only training entrypoint; real loop pending. |
| `training/export_onnx.py` | Boundary | dry-run/help tests | X86-only ONNX export entrypoint; adapter pending. |
| `training/build_tensorrt.py` | Boundary | dry-run/help tests | TensorRT build entrypoint; requires trtexec/hardware. |
| `scripts/phase18_check.py` | Complete baseline | phase18 gate | Dataset/training/export governance gate. |