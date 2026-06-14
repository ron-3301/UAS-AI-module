from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_json_assets_parse() -> None:
    paths = list(ROOT.glob("schemas/**/*.json")) + list(ROOT.glob("sim/**/*.json"))
    assert paths
    for path in paths:
        json.loads(path.read_text())


def test_label_studio_xml_parses() -> None:
    ET.parse(ROOT / "labeling" / "label_studio_project.xml")


def test_airsim_waypoints_shape() -> None:
    waypoints = json.loads((ROOT / "sim" / "airsim_waypoints.json").read_text())
    assert isinstance(waypoints, list)
    assert len(waypoints) >= 1
    for waypoint in waypoints:
        assert {"x", "y", "z", "yaw_deg", "dwell_s", "n_frames"} <= set(waypoint)
        assert waypoint["n_frames"] > 0
        assert waypoint["dwell_s"] >= 0


def test_runtime_requirements_exclude_torch_family() -> None:
    req_lines = (ROOT / "requirements" / "requirements-runtime.txt").read_text().splitlines()
    package_lines = [line.strip().lower() for line in req_lines if line.strip() and not line.strip().startswith("#")]
    forbidden = ("torch", "torchvision", "torchaudio", "ultralytics")
    for line in package_lines:
        assert not line.startswith(forbidden)
