# tests for the w8 evaluator (dry-run path).
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from training import eval as evalmod  # noqa: E402


def test_dry_run_writes_all_reports(tmp_path: Path) -> None:
    result = evalmod.run(
        weights=Path("/dev/null"), data_yaml=Path("/dev/null"),
        device="cpu", out_dir=tmp_path, target_map50=0.80, dry_run=True,
    )
    assert (tmp_path / "results.json").is_file()
    assert (tmp_path / "per_class_ap.csv").is_file()
    assert (tmp_path / "confusion_matrix.csv").is_file()
    assert (tmp_path / "error_report.md").is_file()

    # results.json round-trip
    j = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert j["map50"] == result.map50

    # per_class_ap.csv is sorted ascending
    with open(tmp_path / "per_class_ap.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    aps = [float(r["ap50"]) for r in rows]
    assert aps == sorted(aps), f"per_class CSV not sorted: {aps}"

    # error_report.md mentions the worst class for W9 follow-up
    md = (tmp_path / "error_report.md").read_text(encoding="utf-8")
    worst = min(result.per_class_ap.items(), key=lambda kv: kv[1])[0]
    assert "Recommended next step (W9)" in md
    assert worst in md


def test_main_returns_nonzero_when_below_target(tmp_path: Path) -> None:
    from unittest.mock import patch
    argv = ["eval.py", "--data", "/dev/null", "--out-dir", str(tmp_path),
            "--target-map50", "0.99", "--dry-run"]
    with patch.object(sys, "argv", argv):
        rc = evalmod.main()
    assert rc == 1


def test_main_returns_zero_when_above_target(tmp_path: Path) -> None:
    from unittest.mock import patch
    argv = ["eval.py", "--data", "/dev/null", "--out-dir", str(tmp_path),
            "--target-map50", "0.5", "--dry-run"]
    with patch.object(sys, "argv", argv):
        rc = evalmod.main()
    assert rc == 0
