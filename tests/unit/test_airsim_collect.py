# tests for the parts of airsim_collect.py that don't need airsim.
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts import airsim_collect as ac  # noqa: E402


def test_load_waypoints_ok(tmp_path: Path) -> None:
    wp = tmp_path / "wp.json"
    wp.write_text(json.dumps([
        {"x": 1.0, "y": 2.0, "z": -10.0, "yaw_deg": 90.0},
        {"x": 5.0, "y": 6.0, "z": -20.0},  # missing optional fields -> defaults
    ]), encoding="utf-8")
    wps = ac.load_waypoints(wp)
    assert len(wps) == 2
    assert wps[0].yaw_deg == 90.0
    assert wps[1].dwell_s == 0.5 and wps[1].n_frames == 5


def test_load_waypoints_empty_fails(tmp_path: Path) -> None:
    wp = tmp_path / "wp.json"
    wp.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        ac.load_waypoints(wp)


def test_prepare_dataset_layout(tmp_path: Path) -> None:
    dst = tmp_path / "synth_run"
    ac.prepare_dataset_layout(dst)
    assert (dst / "images" / "train").is_dir()
    assert (dst / "labels" / "train").is_dir()
    yaml_text = (dst / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 7" in yaml_text
    assert "Vehicle-Tracked" in yaml_text


def test_dry_run_main(tmp_path: Path) -> None:
    wp = tmp_path / "wp.json"
    wp.write_text(json.dumps([{"x": 0, "y": 0, "z": -10}]), encoding="utf-8")
    dst = tmp_path / "synth_dry"
    argv = ["airsim_collect.py", "--run-id", "t01",
            "--waypoints", str(wp), "--dst", str(dst), "--dry-run", "--n-frames", "1"]
    with patch.object(sys, "argv", argv):
        rc = ac.main()
    assert rc == 0
    assert (dst / "data.yaml").is_file()


def test_object_regexes_cover_all_classes() -> None:
    # Every class in OUR_CLASS_NAMES must be reachable by at least one regex.
    targeted = {cid for _, cid in ac.OBJECT_REGEXES}
    assert targeted == set(range(len(ac.OUR_CLASS_NAMES)))


def test_airsim_waypoints_sample_loads() -> None:
    sample = REPO / "configs" / "airsim_waypoints.json"
    wps = ac.load_waypoints(sample)
    assert len(wps) >= 4
