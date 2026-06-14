# Architecture Decisions

## ADR-001 — Rebuild around safety-first runtime core

**Decision:** Rebuild the minimum advisory runtime first instead of recreating all 12 historical phases at once.

**Reason:** The uploaded project summary contained broad claims plus many listed production gaps. A small tested baseline is safer and easier to audit.

## ADR-002 — Advisory-only output is enforced in code and schema

**Decision:** Output packets and recommendations always include `advisory_only: true`.

**Reason:** The module must not directly command a vehicle, weapon, or engagement action.

## ADR-003 — Runtime excludes PyTorch-family packages

**Decision:** `requirements-runtime.txt` excludes `torch`, `torchvision`, `torchaudio`, and `ultralytics`; a guard script enforces this.

**Reason:** Jetson runtime should use ONNX Runtime/TensorRT only.

## ADR-004 — Runtime model artifacts reject `.pt` and `.pth`

**Decision:** Runtime detectors/classifiers accept `.onnx`/`.engine` boundaries and reject PyTorch checkpoint files.

**Reason:** Training checkpoints belong to x86 training/export workflows, not runtime deployment.

## ADR-005 — Phase 13 gate is executable

**Decision:** `scripts/phase13_check.py` is the canonical stabilization gate.

**Reason:** Documentation-only readiness is insufficient; Phase 13 requires repeatable checks.

## ADR-006 — Real hardware backends remain boundaries until audited

**Decision:** TensorRT, MAVLink, camera, and terrain-backed geolocation are represented as clear boundaries or mocks.

**Reason:** Fake implementations would create false readiness. Real integrations should be added with hardware-specific tests.
