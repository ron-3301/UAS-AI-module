from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_jetson_health_check_script_passes_in_dev_environment() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/jetson_health_check.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["ok"] is True
    assert {check["name"] for check in result["checks"]} == {
        "runtime_dependency_guard",
        "dry_run_advisory",
    }
