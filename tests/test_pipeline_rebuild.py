from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from uas_ai_module.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_pipeline_emits_advisory_packet() -> None:
    result = Pipeline.dry_run(uas_id="unit-test-uas").run_once()
    packet = result.advisory
    assert packet["schema_version"] == "1.1"
    assert packet["advisory_only"] is True
    assert packet["uas_id"] == "unit-test-uas"
    assert packet["health"]["status"] in {"ok", "degraded", "invalid"}
    assert len(packet["detections"]) == 1


def test_cli_dry_run_outputs_json() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uas_ai_module.cli",
            "--dry-run",
            "--uas-id",
            "cli-test-uas",
            "--validate-output-schema",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    packet = json.loads(proc.stdout)
    assert packet["uas_id"] == "cli-test-uas"
    assert packet["advisory_only"] is True
