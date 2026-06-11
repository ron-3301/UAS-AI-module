# Phase 1 — Acceptance Checklist

> Per `docs/05_phases.md`, Phase 1 (W1-W2) is "Foundations". This file is the
> ground-truth checklist of what "Phase 1 done" means in this repo. Tick a box
> only when the linked artefact exists *and* the command in the right-hand
> column exits 0.

## W1 — Foundations

| # | Deliverable                                       | Artefact                                                                 | Verify command                                                       | Done |
|---|---------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------------|------|
| 1 | Repo skeleton matches Doc 3                       | `src/`, `tests/`, `training/`, `scripts/`, `configs/`, `docs/`, `data/`  | `find . -maxdepth 2 -type d`                                         | ✅   |
| 2 | All 15 design documents present                   | `docs/01_..` through `docs/15_..`                                        | `ls docs/ \| wc -l` → 16 (15 + this file)                            | ✅   |
| 3 | Dockerfile (x86 dev + Jetson) + compose           | `Dockerfile`, `docker-compose.yml`                                       | `docker compose config -q`                                           | ✅   |
| 4 | Config system: YAML + JSON-Schema validation      | `configs/*.yaml` + `configs/schemas/*.schema.json` + `src/config.py`     | `python scripts/validate_configs.py`                                 | ✅   |
| 5 | Centralised logging                               | `src/logging_setup.py`                                                   | `python -m src.cli --config configs/inference.yaml --dry-run`        | ✅   |
| 6 | CLI entry point with override precedence          | `src/cli.py`                                                             | `python -m src.cli --config configs/inference.yaml --dry-run`        | ✅   |
| 7 | Decision log seeded                               | `DECISIONS.md`                                                           | `grep -c '^## DEC-' DECISIONS.md` → ≥ 4                              | ✅   |
| 8 | Unit tests + CI workflow                          | `tests/unit/`, `.github/workflows/ci.yml`                                | `pytest tests/unit/`                                                 | ✅   |
| 9 | DVC config (remote stub OK)                       | `.dvc/config`                                                            | `cat .dvc/config`                                                    | ✅   |
| 10| Pre-commit + lint pipeline                        | `.pre-commit-config.yaml`, `pyproject.toml` (ruff, mypy)                 | `ruff check src/ tests/ training/ scripts/`                          | ✅   |
| 11| Safety contract enforced in code AND locked by tests | `src/output/json_serializer.py` + `tests/unit/test_json_serializer.py` | `pytest tests/unit/test_json_serializer.py`                          | ✅   |

## W2 — Baseline detection pipeline-proof

| # | Deliverable                                       | Artefact                                                                 | Verify command                                                       | Done |
|---|---------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------------|------|
| 12| DOTA → YOLO converter (7-class taxonomy)          | `scripts/convert_dota.py`                                                | `pytest tests/unit/test_convert_dota.py`                             | ✅   |
| 13| Dataset quality gates (Doc 4 §5)                  | `scripts/dataset_stats.py`                                               | `pytest tests/unit/test_dataset_stats.py`                            | ✅   |
| 14| Trainer wired to Ultralytics + W2 acceptance gate | `training/train_detector.py`                                             | `python training/train_detector.py --dry-run`                        | ✅   |
| 15| Baseline run: YOLOv8n on DOTA, mAP@50 ≥ 0.40      | `runs/detector/baseline_w2_yolov8n_dota/summary.json`                    | `jq '.map50 >= 0.40' runs/detector/.../summary.json` → `true`        | ⏳ requires GPU + DOTA download |

**Item 15** is the only gate that requires a GPU and the DOTA dataset (≈ 20 GB).
All preceding gates run in CI on a CPU runner in < 2 minutes. The runtime
acceptance below is verifiable in the sandbox:

```bash
make verify-phase1
```

## Sign-off

Phase 1 is considered **closed** when items 1-14 are ticked. Item 15 is a
*pipeline*-proof gate that lives at the W2/Phase 2 boundary and is signed off
on the dev GPU box.

When closing Phase 1:
1. Add `DECISIONS.md` entry under category `Tooling` titled "Phase 1 closed".
2. Tag the commit `phase-1`.
3. Open the first Phase-2 issue.
