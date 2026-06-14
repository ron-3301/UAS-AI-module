#!/usr/bin/env python3
"""ONNX Runtime metadata/session smoke test.

Dry-run mode validates the metadata sidecar only. Real mode imports onnxruntime,
opens the model artifact, and compares basic input/output names when possible.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.model_metadata import load_model_metadata  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ONNX Runtime model smoke test")
    parser.add_argument("metadata", help="Model metadata JSON sidecar")
    parser.add_argument("--providers", nargs="*", default=["CPUExecutionProvider"])
    parser.add_argument("--verify-hash", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate metadata without opening ONNX Runtime")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = load_model_metadata(args.metadata, verify_hash=(args.verify_hash and not args.dry_run))
    result = {
        "ok": True,
        "mode": "dry-run" if args.dry_run else "onnxruntime",
        "name": metadata.name,
        "role": metadata.role,
        "artifact": str(metadata.artifact),
        "input_name": metadata.input_name,
        "output_names": list(metadata.output_names),
    }
    if args.dry_run:
        print(json.dumps(result, sort_keys=True))
        return 0

    try:
        import onnxruntime as ort  # type: ignore
    except Exception as exc:
        print(f"onnxruntime import failed: {exc}", file=sys.stderr)
        return 2
    if not metadata.artifact.exists():
        print(f"artifact not found: {metadata.artifact}", file=sys.stderr)
        return 3
    session = ort.InferenceSession(str(metadata.artifact), providers=args.providers)
    input_names = [item.name for item in session.get_inputs()]
    output_names = [item.name for item in session.get_outputs()]
    result["session_inputs"] = input_names
    result["session_outputs"] = output_names
    result["input_name_match"] = metadata.input_name in input_names
    result["output_name_match"] = all(name in output_names for name in metadata.output_names)
    result["ok"] = bool(result["input_name_match"] and result["output_name_match"])
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
