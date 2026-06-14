#!/usr/bin/env python3
"""Record read-only MAVLink telemetry samples to JSONL."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.ingestion.mavlink import MavlinkTelemetrySource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record read-only MAVLink telemetry samples")
    parser.add_argument("--endpoint", default="udp:0.0.0.0:14550")
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--timeout-s", type=float, default=1.0)
    parser.add_argument("--output", help="Output JSONL path")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def telemetry_to_dict(sample) -> dict:
    return {
        "timestamp_utc": sample.timestamp_utc.isoformat(),
        "lat_deg": sample.lat_deg,
        "lon_deg": sample.lon_deg,
        "alt_msl_m": sample.alt_msl_m,
        "alt_agl_m": sample.alt_agl_m,
        "roll_deg": sample.roll_deg,
        "pitch_deg": sample.pitch_deg,
        "yaw_deg": sample.yaw_deg,
        "velocity_ned_mps": list(sample.velocity_ned_mps),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.samples <= 0:
        print("--samples must be positive", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "samples": args.samples, "endpoint": args.endpoint}, sort_keys=True))
        return 0
    source = MavlinkTelemetrySource(endpoint=args.endpoint, timeout_s=args.timeout_s)
    rows = [telemetry_to_dict(source.read()) for _ in range(args.samples)]
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    else:
        for row in rows:
            print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
