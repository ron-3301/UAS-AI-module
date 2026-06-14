from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from uas_ai_module.output.golden import compare_packets, normalize_packets
from uas_ai_module.pipeline import Pipeline
from uas_ai_module.release.sbom import parse_requirements_file
from uas_ai_module.release.source_manifest import build_source_manifest

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=True)


def test_golden_replay_matches_fixture() -> None:
    pipeline = Pipeline.replay(str(ROOT / "tests" / "fixtures" / "replay" / "sample_mission.json"), uas_id="uas-golden")
    actual = normalize_packets([pipeline.run_once().advisory, pipeline.run_once().advisory])
    expected = json.loads((ROOT / "tests" / "fixtures" / "replay" / "sample_mission.golden.json").read_text())
    assert compare_packets(actual, expected) == []


def test_golden_replay_script_compare_passes() -> None:
    proc = run([
        sys.executable,
        "scripts/generate_golden_replay.py",
        "tests/fixtures/replay/sample_mission.json",
        "--steps",
        "2",
        "--uas-id",
        "uas-golden",
        "--compare",
        "tests/fixtures/replay/sample_mission.golden.json",
    ])
    assert json.loads(proc.stdout)["ok"] is True


def test_release_manifest_contains_source_file() -> None:
    manifest = build_source_manifest(ROOT)
    paths = {item.path for item in manifest.files}
    assert "src/uas_ai_module/pipeline.py" in paths
    assert manifest.file_count > 0


def test_sbom_parses_runtime_requirements() -> None:
    entries = parse_requirements_file(ROOT / "requirements" / "requirements-runtime.txt")
    names = {entry.name for entry in entries}
    assert "numpy" in names
    assert "torch" not in names


def test_phase16_scripts_dry_run_and_help() -> None:
    commands = [
        [sys.executable, "scripts/build_release_manifest.py", "--dry-run"],
        [sys.executable, "scripts/generate_sbom.py", "--dry-run"],
        [sys.executable, "scripts/generate_golden_replay.py", "tests/fixtures/replay/sample_mission.json", "--steps", "1", "--dry-run"],
        [sys.executable, "scripts/phase16_check.py", "--dry-run"],
        [sys.executable, "scripts/phase16_check.py", "--help"],
    ]
    for command in commands:
        proc = run(command)
        assert proc.stdout
