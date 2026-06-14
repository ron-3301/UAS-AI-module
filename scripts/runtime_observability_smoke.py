#!/usr/bin/env python3
"""Runtime metrics/logging smoke test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.metrics.runtime_metrics import RuntimeMetricsCollector, prometheus_text  # noqa: E402
from uas_ai_module.output.jsonl_logger import AdvisoryJsonlLogger  # noqa: E402
from uas_ai_module.pipeline import Pipeline  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run dry-run pipeline and extract runtime observability outputs")
    parser.add_argument("--log-jsonl", help="Optional JSONL path to append advisory packet")
    parser.add_argument("--prometheus", action="store_true", help="Include Prometheus text exposition in output")
    parser.add_argument("--dry-run", action="store_true", help="Validate observability path without persistent writes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = Pipeline.dry_run("observability-smoke").run_once().advisory
    snapshot = RuntimeMetricsCollector().from_packet(packet)
    if args.log_jsonl and not args.dry_run:
        AdvisoryJsonlLogger(args.log_jsonl).write(packet)
    result = {
        "ok": True,
        "mode": "dry-run" if args.dry_run else "check",
        "metrics": {
            "health_status": snapshot.health_status,
            "latency_ms": snapshot.latency_ms,
            "detection_count": snapshot.detection_count,
            "invalid_detection_count": snapshot.invalid_detection_count,
            "warning_count": snapshot.warning_count,
        },
    }
    if args.prometheus:
        result["prometheus"] = prometheus_text(snapshot)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
