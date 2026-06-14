"""Command line interface for the rebuilt core."""
from __future__ import annotations

import argparse
import json
import sys

from uas_ai_module.config import ConfigError, load_config
from uas_ai_module.output.schema_validator import AdvisorySchemaValidator, OutputValidationError
from uas_ai_module.pipeline import Pipeline
from uas_ai_module.runtime_factory import RuntimeFactoryError, build_pipeline_from_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UAS AI Module advisory runtime")
    parser.add_argument("--config", help="Path to inference JSON/YAML config")
    parser.add_argument(
        "--runtime-schema",
        default="inference_runtime.schema.json",
        help="Config schema under schemas/config/ to use for --config validation",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run one deterministic mocked pipeline pass")
    parser.add_argument("--run-once", action="store_true", help="Run one config-built runtime pipeline pass")
    parser.add_argument(
        "--allow-mock-backends",
        action="store_true",
        help="Testing only: build mock detector/frame/telemetry backends while still validating config",
    )
    parser.add_argument("--replay", help="Path to a mission replay manifest JSON")
    parser.add_argument("--replay-steps", type=int, default=1, help="Number of replay frames to process")
    parser.add_argument("--uas-id", default="uas-dry-run", help="UAS/node identifier for output packets")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument(
        "--validate-output-schema",
        action="store_true",
        help="Validate emitted advisory packet(s) against schemas/output/advisory_v1_1.schema.json",
    )
    return parser


def _validate_packet_if_requested(packet: dict, enabled: bool) -> None:
    if enabled:
        AdvisorySchemaValidator().validate(packet)


def _print_packets(packets: list[dict], *, pretty: bool, serializer=None) -> None:
    if pretty:
        print(json.dumps(packets[0] if len(packets) == 1 else packets, indent=2, sort_keys=True))
    else:
        for packet in packets:
            if serializer and len(packets) == 1:
                print(serializer.dumps(packet))
            else:
                print(json.dumps(packet, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = None
    if args.config:
        try:
            config = load_config(args.config, args.runtime_schema, runtime=True)
        except ConfigError as exc:
            print(f"config error: {exc}", file=sys.stderr)
            return 2

    if args.replay:
        if args.replay_steps <= 0:
            parser.error("--replay-steps must be positive")
        pipeline = Pipeline.replay(args.replay, uas_id=args.uas_id)
        packets = []
        try:
            for _ in range(args.replay_steps):
                result = pipeline.run_once()
                _validate_packet_if_requested(result.advisory, args.validate_output_schema)
                packets.append(result.advisory)
        except (EOFError, OutputValidationError) as exc:
            print(f"replay error: {exc}", file=sys.stderr)
            return 3
        _print_packets(packets, pretty=args.pretty)
        return 0

    if args.run_once:
        if config is None:
            parser.error("--run-once requires --config")
        try:
            pipeline = build_pipeline_from_config(
                config,
                uas_id=args.uas_id,
                allow_mock_backends=args.allow_mock_backends,
            )
            result = pipeline.run_once()
            _validate_packet_if_requested(result.advisory, args.validate_output_schema)
        except (RuntimeFactoryError, FileNotFoundError, RuntimeError, OutputValidationError) as exc:
            print(f"runtime error: {exc}", file=sys.stderr)
            return 4
        _print_packets([result.advisory], pretty=args.pretty, serializer=pipeline.serializer)
        return 0

    if args.dry_run:
        pipeline = Pipeline.dry_run(uas_id=args.uas_id)
        result = pipeline.run_once()
        try:
            _validate_packet_if_requested(result.advisory, args.validate_output_schema)
        except OutputValidationError as exc:
            print(f"output schema error: {exc}", file=sys.stderr)
            return 3
        _print_packets([result.advisory], pretty=args.pretty, serializer=pipeline.serializer)
        return 0

    if args.config:
        print("config validation passed")
        return 0

    parser.error("choose one mode: --dry-run, --replay, --run-once, or --config validation")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
