#!/usr/bin/env python3
"""Read-only MAVLink telemetry smoke test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.ingestion.mavlink import MavlinkTelemetrySource  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only MAVLink telemetry smoke test")
    parser.add_argument("--endpoint", default="udp:0.0.0.0:14550")
    parser.add_argument("--timeout-s", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true", help="Validate arguments without opening MAVLink")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout_s <= 0:
        print("timeout must be positive", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "endpoint": args.endpoint}, sort_keys=True))
        return 0
    telemetry = MavlinkTelemetrySource(endpoint=args.endpoint, timeout_s=args.timeout_s).read()
    print(json.dumps({
        "ok": True,
        "lat_deg": telemetry.lat_deg,
        "lon_deg": telemetry.lon_deg,
        "alt_msl_m": telemetry.alt_msl_m,
        "alt_agl_m": telemetry.alt_agl_m,
        "yaw_deg": telemetry.yaw_deg,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
