#!/usr/bin/env python3
"""Validate available project assets and schemas."""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


def iter_json_files() -> Iterable[Path]:
    yield from ROOT.glob("schemas/**/*.json")
    yield from ROOT.glob("sim/**/*.json")
    yield from ROOT.glob("configs/**/*.json")
    yield from ROOT.glob("models/**/*.json")
    yield from ROOT.glob("tests/fixtures/**/*.json")


def check_json_parse() -> list[str]:
    errors: list[str] = []
    for path in sorted(iter_json_files()):
        try:
            json.loads(path.read_text())
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"JSON parse failed: {path.relative_to(ROOT)}: {exc}")
    return errors


def check_xml_parse() -> list[str]:
    errors: list[str] = []
    for path in sorted(ROOT.glob("labeling/**/*.xml")):
        try:
            ET.parse(path)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"XML parse failed: {path.relative_to(ROOT)}: {exc}")
    return errors


def check_json_schemas_if_possible() -> list[str]:
    errors: list[str] = []
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        print("jsonschema not installed; skipping Draft-07 schema syntax checks")
        return errors

    for path in sorted(ROOT.glob("schemas/**/*.schema.json")):
        try:
            schema = json.loads(path.read_text())
            Draft7Validator.check_schema(schema)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"Schema check failed: {path.relative_to(ROOT)}: {exc}")
    return errors


def check_airsim_waypoints() -> list[str]:
    errors: list[str] = []
    path = ROOT / "sim" / "airsim_waypoints.json"
    if not path.exists():
        return ["Missing sim/airsim_waypoints.json"]

    data = json.loads(path.read_text())
    if not isinstance(data, list) or not data:
        return ["AirSim waypoints must be a non-empty list"]

    required = {"x", "y", "z", "yaw_deg", "dwell_s", "n_frames"}
    for idx, waypoint in enumerate(data):
        if not isinstance(waypoint, dict):
            errors.append(f"Waypoint {idx} is not an object")
            continue
        missing = sorted(required - waypoint.keys())
        if missing:
            errors.append(f"Waypoint {idx} missing fields: {missing}")
        if waypoint.get("n_frames", 0) <= 0:
            errors.append(f"Waypoint {idx} must have n_frames > 0")
        if waypoint.get("dwell_s", -1) < 0:
            errors.append(f"Waypoint {idx} must have dwell_s >= 0")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate project assets and JSON schemas")
    parser.add_argument("--no-schema-check", action="store_true", help="Skip Draft-07 schema syntax checks")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    errors: list[str] = []
    errors.extend(check_json_parse())
    errors.extend(check_xml_parse())
    if not args.no_schema_check:
        errors.extend(check_json_schemas_if_possible())
    errors.extend(check_airsim_waypoints())

    if errors:
        print("Asset validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Asset validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
