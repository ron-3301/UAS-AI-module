from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from uas_ai_module.ingestion.replay import ReplayDataset, ReplayFrameSource, ReplayTelemetrySource
from uas_ai_module.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "tests" / "fixtures" / "replay" / "sample_mission.json"


def test_replay_dataset_synchronizes_frame_and_telemetry() -> None:
    dataset = ReplayDataset.from_manifest(REPLAY)
    frame_source = ReplayFrameSource(dataset)
    telemetry_source = ReplayTelemetrySource(dataset)

    frame1 = frame_source.read()
    telemetry1 = telemetry_source.read()
    assert frame1.frame_id == "replay-000001"
    assert frame1.data.shape == (480, 640, 3)
    assert telemetry1.lat_deg == pytest.approx(28.6139)

    frame2 = frame_source.read()
    telemetry2 = telemetry_source.read()
    assert frame2.frame_id == "replay-000002"
    assert telemetry2.yaw_deg == pytest.approx(5.0)

    with pytest.raises(EOFError):
        frame_source.read()


def test_pipeline_replay_emits_valid_advisory() -> None:
    pipeline = Pipeline.replay(str(REPLAY), uas_id="replay-test-uas")
    result = pipeline.run_once()
    assert result.advisory["uas_id"] == "replay-test-uas"
    assert result.advisory["mission_profile"] == "replay"
    assert result.advisory["advisory_only"] is True
    assert len(result.advisory["detections"]) == 1


def test_cli_replay_outputs_ndjson_for_multiple_steps() -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "uas_ai_module.cli",
            "--replay",
            str(REPLAY),
            "--replay-steps",
            "2",
            "--uas-id",
            "cli-replay-uas",
            "--validate-output-schema",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    packets = [json.loads(line) for line in lines]
    assert [packet["frame_id"] for packet in packets] == ["replay-000001", "replay-000002"]
    assert all(packet["uas_id"] == "cli-replay-uas" for packet in packets)


def test_replay_script_outputs_pretty_json() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/replay_mission.py",
            str(REPLAY),
            "--steps",
            "1",
            "--pretty",
            "--validate-output-schema",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    packet = json.loads(proc.stdout)
    assert packet["advisory_only"] is True
