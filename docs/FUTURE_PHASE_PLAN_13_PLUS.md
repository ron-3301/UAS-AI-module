# UAS AI Module – Future Phase Plan (Phase 13+)

Prepared after reviewing `PROJECT_SUMMARY_PHASES_1-12.md`.

## Current Interpretation

The project is described as complete through Phase 12, but many phase sections still list important production gaps: placeholder training logic, incomplete real I/O, missing schemas, missing generated protobufs, incomplete TensorRT/hardware integration, incomplete simulation/HIL, and incomplete OTA/security hardening.

The next work should therefore not immediately add speculative features. It should first turn the existing implementation into a verified, production-ready, advisory-only UAS perception/coordination/fleet-management stack.

## Non-Negotiable Project Constraints

1. Jetson runtime uses TensorRT + ONNX Runtime only.
2. No PyTorch/torchvision/torchaudio on Jetson runtime.
3. All heavy scripts must support `--dry-run`.
4. Hard-coded safety filters must remain non-configurable.
5. Any new YAML config section must have a JSON schema.
6. The system remains advisory-only and must not directly command vehicle behavior without explicit external human/operator authorization layers.
7. Safety-critical failures should fail closed: degraded output, invalid recommendation, or explicit health warning rather than silent bad output.

---

## Phase 13 – Repository Reality Audit & Stabilization

### Goal
Establish the true state of the codebase and create a stable foundation for all future work.

### Work Items
- Inventory all files, modules, scripts, tests, configs, schemas, docs, and generated artifacts.
- Identify placeholder implementations versus real implementations.
- Build an implementation-status matrix for every module mentioned in the Phase 1–12 summary.
- Add or repair packaging metadata, imports, and module boundaries.
- Add `.gitignore`, `LICENSE`, `README.md`, `DECISIONS.md`, and `CHANGELOG.md` if missing.
- Add CI checks for importability and `--dry-run` execution of heavy scripts.
- Add a runtime dependency audit that fails if forbidden runtime dependencies are introduced.

### Deliverables
- `docs/implementation_audit.md`
- `docs/module_status_matrix.md`
- Baseline unit test suite
- Baseline CI/check script
- Clean project structure

### Acceptance Criteria
- All source modules import successfully.
- All CLI scripts expose `--help`.
- All heavy scripts support `--dry-run`.
- Runtime dependency scan confirms no PyTorch packages are required by Jetson runtime.
- The project can run a mocked end-to-end pipeline locally.

---

## Phase 14 – Safety Contract, Config Schemas & Output Validation

### Goal
Lock down the safety-critical behavior and remove ambiguity from configuration/output formats.

### Work Items
- Add JSON schemas for all config sections introduced after Phase 6:
  - adaptation
  - coordination
  - prediction
  - autonomy
  - robustness
  - fusion
  - updater
  - metrics
  - logging/fleet
- Add versioned schemas for JSON advisory output.
- Add safety regression tests around hard-coded serializer rules:
  - detection confidence threshold
  - civilian suppression
  - person-below-AGL rule
  - CEP invalidation
  - advisory-only flags
- Add fail-closed behavior for missing telemetry, stale frames, stale tracks, invalid camera calibration, and invalid geolocation.
- Add structured error/warning fields to output where appropriate.

### Deliverables
- `schemas/config/*.schema.json`
- `schemas/output/advisory_v*.schema.json`
- `tests/safety/`
- Updated `docs/safety_contract.md`

### Acceptance Criteria
- Invalid configs are rejected with actionable errors.
- All output packets validate against schema.
- Safety filters cannot be disabled through YAML/config/env/CLI.
- Failure scenarios emit explicit degraded/invalid advisory status.

---

## Phase 15 – Core Algorithm Completion

### Goal
Replace simplified/placeholder algorithmic logic with tested, deterministic implementations.

### Work Items
- Complete IMM Kalman prediction/update equations for CV/CT/braking models.
- Complete TCPA and closest-point geometry using track state, ownship state, covariance, and units validation.
- Implement robust detector ensemble fusion using IoU/NMS or weighted boxes fusion.
- Complete adaptive thresholding using real entropy/confidence statistics.
- Complete domain-discriminator ONNX inference path and export contract.
- Complete TensorRT/ONNX wrapper error handling and metadata validation.
- Improve crop extraction, track association, and federated Kalman consistency checks.

### Deliverables
- Production implementations for incomplete algorithm modules
- Numerical unit tests with fixtures
- Synthetic trajectory tests
- Benchmarks for per-stage latency

### Acceptance Criteria
- IMM/TCPA pass deterministic numerical tests.
- Ensemble fusion improves or preserves validation metrics on fixture data.
- ONNX/TensorRT wrappers fail clearly on incompatible models.
- p95 latency budget remains compatible with the project target.

---

## Phase 16 – Real Data Pipeline, Training, Export & Model Governance

### Goal
Make training-side tooling real while preserving Jetson runtime restrictions.

### Work Items
- Implement real file I/O for DOTA, VEDAI, xView, and any project-native datasets.
- Implement dataset validation, deduplication, stratified splits, provenance, and class-balance reports.
- Add dataset versioning plan, preferably DVC or a lightweight manifest system.
- Implement x86-only PyTorch training loops for detector, classifier, behaviour LSTM, and domain discriminator.
- Export trained models to ONNX and TensorRT engines.
- Add model metadata: input shapes, class map, calibration info, training data version, metrics, hash.
- Add model cards and evaluation reports.

### Deliverables
- Real converter/merger/stat scripts
- Training pipeline with dry-run mode
- ONNX/TensorRT export scripts
- `models/manifest.json`
- `docs/model_governance.md`

### Acceptance Criteria
- A fresh dataset can be converted, merged, validated, trained on, and exported reproducibly.
- Training dependencies stay isolated from Jetson runtime dependencies.
- Every deployed model has a version, hash, metrics report, and rollback path.

---

## Phase 17 – Simulation, Replay, Integration & HIL Test Harness

### Goal
Validate the full stack before field/hardware trials.

### Work Items
- Build deterministic replay harness for camera frames + MAVLink telemetry.
- Complete SITL integration using PX4/ArduPilot-compatible telemetry streams.
- Add AirSim/Gazebo scenario runner if project environment supports it.
- Add mission scenario library:
  - nominal tracking
  - lost telemetry
  - camera dropout
  - GNSS spoof signal
  - degraded visibility
  - high-latency mesh
  - thermal-only fallback
- Test advisory waypoint generation without direct vehicle control.
- Add golden JSON outputs for replay regression.

### Deliverables
- `scripts/replay_mission.py`
- `scripts/run_sitl_scenarios.py`
- `tests/integration/`
- `tests/hil/`
- Scenario fixtures and golden outputs

### Acceptance Criteria
- End-to-end replay produces deterministic advisory JSON.
- HIL/SITL tests run in CI or documented local environment.
- Degraded sensor conditions produce safe degraded outputs.
- No test requires live hardware unless marked as hardware-only.

---

## Phase 18 – Jetson Production Runtime & Hardware Bring-Up

### Goal
Move from local/mocked execution to reliable Jetson deployment.

### Work Items
- Implement real TensorRT engine loading and warm-up.
- Implement camera ingestion for visible and thermal cameras.
- Add hardware telemetry collection using Jetson-compatible tools.
- Implement thermal/power fallback modes.
- Add systemd service, environment files, log rotation, health checks, and watchdog behavior.
- Benchmark end-to-end latency, memory, power, temperature, and FPS.
- Add offline install/deployment instructions.

### Deliverables
- `deploy/systemd/uas-ai-module.service`
- `deploy/jetson_setup.md`
- `scripts/jetson_health_check.py`
- Hardware benchmark reports

### Acceptance Criteria
- Jetson runtime starts cleanly after reboot.
- p95 latency target is measured and documented.
- Thermal/power fallback engages under stress.
- Logs and metrics are accessible without manual shell inspection.

---

## Phase 19 – Coordination Mesh, Bandwidth Control & Secure Communications

### Goal
Productionize multi-UAS coordination while protecting integrity and availability.

### Work Items
- Generate and commit/build protobuf Python artifacts or add generation step.
- Implement real ZeroMQ publish/subscribe behavior.
- Add bandwidth monitoring, compression, rate limits, TTL, stale-message dropping, and backpressure.
- Add message authentication and optional encryption.
- Add node identity, key rotation, replay protection, and monotonic timestamps.
- Add simulation tests for packet loss, delay, out-of-order delivery, and partial fleet failure.

### Deliverables
- Real generated protobuf flow
- Mesh integration tests
- `docs/mesh_protocol.md`
- Secure communication/key-management notes

### Acceptance Criteria
- Multi-node local simulation shares and fuses tracks correctly.
- Bandwidth usage remains below configured limits.
- Stale or unauthenticated messages are rejected.
- Mesh failure degrades gracefully to local-only mode.

---

## Phase 20 – OTA, Observability & Fleet Operations

### Goal
Make fleet deployment maintainable and recoverable.

### Work Items
- Replace simple OTA server with HTTPS-backed signed manifest flow.
- Implement Ed25519 signing and verification for release artifacts.
- Add atomic install and rollback.
- Add canary deployment and staged rollout controls.
- Implement real Prometheus metrics collection from runtime and hardware.
- Harden log aggregation with local buffering, compression, retry, and privacy controls.
- Add operator runbooks for update, rollback, diagnosis, and incident response.

### Deliverables
- Signed OTA release tooling
- OTA server/client docs
- Prometheus dashboard examples
- Fleet runbook v2

### Acceptance Criteria
- Invalid signatures are rejected.
- Interrupted updates roll back safely.
- Metrics cover health, latency, detections, track counts, stale sensors, temperature, power, and error rates.
- Operators can diagnose a failed node from logs/metrics.

---

## Phase 21 – Ground Station, Human Review & Explainability

### Goal
Provide a human-facing interface for advisory outputs and operational trust.

### Work Items
- Build ground-station UI for tracks, confidence, uncertainty, sensor health, and advisory status.
- Add replay viewer for missions and incidents.
- Add explanation fields: why a recommendation is valid/invalid, which safety filters triggered, confidence contributors.
- Add operator annotations and feedback export for later training review.
- Add role-based access controls if deployed across a fleet.

### Deliverables
- Ground station prototype
- Replay/incident viewer
- Human feedback format
- `docs/operator_guide.md`

### Acceptance Criteria
- Operator can understand advisory outputs without reading raw JSON.
- Invalid/degraded recommendations are clearly marked.
- Feedback can be exported into the data governance pipeline.

---

## Phase 22 – Defensive Robustness, Red-Team Testing & Sensor Degradation

### Goal
Stress-test the system against non-ideal field conditions and adversarial inputs defensively.

### Work Items
- Implement real corruptions: blur, dust/sand, rain, fog, compression, motion smear, glare, low light.
- Add defensive adversarial evaluation and mitigations.
- Expand GNSS spoof detection with visual/IMU consistency checks.
- Add thermal/visible cross-validation and fallback behavior.
- Add red-team scenario reports and regression fixtures.

### Deliverables
- Robustness test suite
- Defensive mitigation modules
- Red-team evaluation report
- Updated safety regression suite

### Acceptance Criteria
- Robustness metrics are tracked over releases.
- Known bad/degraded conditions trigger warnings or invalid advisories instead of silent confidence.
- Defensive mitigations do not exceed latency budget.

---

## Phase 23 – Release Candidate, Compliance & Long-Term Maintenance

### Goal
Prepare the project for controlled release and sustainable maintenance.

### Work Items
- Produce a safety case and limitations document.
- Add SBOM generation and vulnerability scanning.
- Add reproducible build instructions.
- Freeze public APIs and schema versions for v1.0.
- Add contribution guidelines and code ownership.
- Add long-term test matrix for x86 dev, CI, Jetson runtime, and HIL.

### Deliverables
- v1.0 release checklist
- SBOM
- Safety case
- Reproducible build docs
- Maintenance plan

### Acceptance Criteria
- v1.0 can be built, tested, deployed, rolled back, and audited.
- Schemas and interfaces are versioned.
- Known limitations are documented clearly.

---

## Recommended Execution Order

### Immediate Sprint
1. Phase 13 audit and stabilization.
2. Add missing tests around safety filters and importability.
3. Add schemas for currently unschematized config sections.
4. Create/update documentation files.

### Next 2–4 Sprints
1. Complete core algorithms from Phase 15.
2. Complete data/training/export pipeline from Phase 16.
3. Build deterministic replay/integration harness from Phase 17.

### Hardware/Fleet Readiness
1. Jetson runtime hardening from Phase 18.
2. Mesh security and bandwidth controls from Phase 19.
3. OTA/observability from Phase 20.

### Productization
1. Ground station and human review from Phase 21.
2. Defensive robustness from Phase 22.
3. Release candidate/compliance from Phase 23.

---

## First Implementation Tasks Once Codebase Is Available

1. Run repository tree inspection and dependency scan.
2. Run existing tests and capture failures.
3. Create `docs/implementation_audit.md`.
4. Add basic import tests for all `src/*` modules.
5. Add `--dry-run` checks for all scripts under `scripts/` and `training/`.
6. Add or update JSON schemas for Phase 7–12 config sections.
7. Add safety regression tests for `src/output/json_serializer.py`.
8. Replace the highest-risk placeholder module with real logic, starting with IMM/TCPA or dataset I/O depending on repo state.
