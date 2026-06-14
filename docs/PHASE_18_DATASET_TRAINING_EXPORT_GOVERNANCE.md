# Phase 18 — Dataset, Training, Export & Model Governance Preparation

Date: 2026-06-14

## Status

Phase 18 is complete for the rebuilt baseline.

This phase prepares the x86-side dataset/training/export governance required
before real ONNX/TensorRT artifacts can be generated and validated. It does not
claim real model training has been performed.

## Implemented

### Dataset governance

Files:

```text
schemas/data/dataset_manifest.schema.json
configs/data/dataset_manifest.example.json
src/uas_ai_module/data/dataset_manifest.py
scripts/validate_dataset_manifest.py
scripts/generate_dataset_report.py
scripts/check_class_balance.py
```

Features:

- dataset ID and taxonomy version tracking
- class list validation
- split metadata
- per-split class counts
- aggregate class-count reporting
- class-balance warnings
- optional referenced-file existence checks

### Export planning

Files:

```text
schemas/models/export_plan.schema.json
configs/models/export_plan.example.json
src/uas_ai_module/data/export_plan.py
scripts/prepare_model_export.py
scripts/write_model_metadata.py
```

Features:

- source training checkpoint path tracking
- ONNX output path tracking
- metadata sidecar output path tracking
- optional TensorRT engine output path tracking
- class-map and input-shape governance
- metadata sidecar preparation

### X86-only training/export entrypoints

Files:

```text
training/train_detector.py
training/export_onnx.py
training/build_tensorrt.py
```

All support `--dry-run`.

Training/export dependencies remain outside Jetson runtime and belong to
`requirements/requirements-dev.txt`.

### Phase 18 gate

File:

```text
scripts/phase18_check.py
```

Runs:

1. Phase 17 gate
2. dataset manifest validation
3. dataset report dry-run
4. class balance check
5. export plan validation
6. model metadata dry-run generation
7. detector training dry-run
8. ONNX export dry-run
9. TensorRT build dry-run

## Validation

Command:

```bash
python scripts/phase18_check.py --stop-on-failure
```

Result:

```text
Phase 18 dataset/training/export governance check passed
pytest: 91 passed
```

## Safety/runtime posture

- No training dependency was added to runtime requirements.
- Training scripts are clearly x86/dev-side only.
- Runtime `.pt`/`.pth` rejection remains enforced.
- Training checkpoints are allowed only in export plans, not runtime configs.
- Advisory-only runtime behavior is unchanged.

## What still requires external work

1. Real dataset manifests from actual converted datasets.
2. Real training implementation with explicit x86-only dependencies.
3. Real ONNX export adapters for selected architectures.
4. Real TensorRT build execution on Jetson or TensorRT-capable environment.
5. Real model metadata sidecars with artifact hashes.

## Recommended next phase

Proceed to Phase 19: implement concrete dataset converters/reporting or real
model export adapters once actual datasets/checkpoints are available.
