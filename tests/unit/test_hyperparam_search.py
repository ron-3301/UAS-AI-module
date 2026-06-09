# tests for the w7 optuna hpo harness (dry-run path).
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from training import hyperparam_search as hpo  # noqa: E402

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("optuna") is None, reason="optuna not installed",
)


def test_dry_run_optimises_synthetic_objective(tmp_path: Path) -> None:
    out = tmp_path / "summary.json"
    results = hpo.run(
        study_name="test_w7", storage=None,
        data=Path("/dev/null"), arch="yolov8m",
        trials=20, trial_epochs=5, device="cpu",
        dry_run=True, out_path=out,
    )
    assert len(results) == 20
    # Best mAP should be close to the synthetic optimum (0.85 ideal).
    best = max(results, key=lambda r: r.map50)
    assert best.map50 >= 0.70, f"best={best.map50}"
    summary = json.loads(out.read_text(encoding="utf-8"))
    assert "best_value" in summary and "best_params" in summary
    for p in ("lr0", "lrf", "momentum", "weight_decay", "warmup_epochs", "mosaic"):
        assert p in summary["best_params"]


def test_dry_run_short_trial_count(tmp_path: Path) -> None:
    results = hpo.run(
        study_name="test_w7_short", storage=None,
        data=Path("/dev/null"), arch="yolov8m",
        trials=3, trial_epochs=1, device="cpu",
        dry_run=True, out_path=tmp_path / "summary.json",
    )
    assert len(results) == 3
