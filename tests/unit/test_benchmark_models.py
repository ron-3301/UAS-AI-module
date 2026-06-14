# tests for the w6 benchmark harness (dry-run path).
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import benchmark_models as bm  # noqa: E402


def test_dry_run_produces_csv_and_md(tmp_path: Path) -> None:
    out_dir = tmp_path / "w6"
    rows, csv_path, md_path = bm.run(
        data_yaml=Path("/dev/null"), epochs=10, device="cpu",
        candidates=["yolov8s", "yolov8m", "rt-detr-l"],
        out_dir=out_dir, dry_run=True,
    )
    assert csv_path.is_file() and md_path.is_file()
    assert len(rows) == 3
    md = md_path.read_text(encoding="utf-8")
    assert "W6 Model Benchmark" in md
    assert "Recommended" in md
    # All three candidates appear
    assert "yolov8s" in md and "yolov8m" in md and "rt-detr-l" in md


def test_recommended_excludes_over_budget(tmp_path: Path) -> None:
    out_dir = tmp_path / "w6"
    rows, _, md_path = bm.run(
        data_yaml=Path("/dev/null"), epochs=10, device="cpu",
        candidates=["yolov8s", "yolov8m", "rt-detr-l"],
        out_dir=out_dir, dry_run=True,
    )
    md = md_path.read_text(encoding="utf-8")
    # rt-detr-l has p95 158 ms (> 110 budget) and should NOT be recommended.
    rec_line = [line for line in md.splitlines() if line.startswith("**Recommended")][0]
    assert "rt-detr-l" not in rec_line


def test_main_prints_json(tmp_path: Path, capsys) -> None:
    from unittest.mock import patch
    argv = ["benchmark_models.py", "--data", "/dev/null", "--dry-run",
            "--out-dir", str(tmp_path / "w6")]
    with patch.object(sys, "argv", argv):
        rc = bm.main()
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "rows" in payload and len(payload["rows"]) == len(bm.DEFAULT_CANDIDATES)
