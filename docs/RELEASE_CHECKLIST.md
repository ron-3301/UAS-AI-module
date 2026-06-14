# Rebuild Baseline Release Checklist

Use this checklist before handing the rebuild to Phase 13.

## Required checks

```bash
python scripts/validate_assets.py
python scripts/check_runtime_deps.py
pytest -q
PYTHONPATH=src python -m uas_ai_module.cli --dry-run --validate-output-schema
PYTHONPATH=src python -m uas_ai_module.cli --replay tests/fixtures/replay/sample_mission.json --replay-steps 2 --validate-output-schema
python scripts/jetson_health_check.py
python scripts/phase13_check.py --stop-on-failure
python scripts/phase14_check.py --stop-on-failure
python scripts/phase15_check.py --stop-on-failure
python scripts/phase16_check.py --stop-on-failure
python scripts/phase17_check.py --stop-on-failure
python scripts/phase18_check.py --stop-on-failure
```

## Expected result

- Asset validation passes.
- Runtime dependency guard passes.
- Test suite passes.
- Dry-run advisory packet validates against schema.
- Replay packets validate against schema.
- Health check passes.

## Current baseline

```text
pytest: 91 passed
```

## Safety checks

- `advisory_only` cannot be disabled by caller-supplied recommendations.
- Runtime `.pt` / `.pth` artifacts are rejected.
- Runtime requirements exclude PyTorch-family packages.
- Civilian suppression regression exists.
- Person-below-AGL regression exists.
- CEP invalidation regression exists.
- Stale telemetry/frame invalidation regressions exist.
