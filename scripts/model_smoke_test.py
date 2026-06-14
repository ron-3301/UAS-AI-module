#!/usr/bin/env python3
"""Model metadata/artifact smoke test."""
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
    parser = argparse.ArgumentParser(description="Validate model metadata sidecar and optionally verify hash")
    parser.add_argument("metadata", help="Path to model metadata JSON sidecar")
    parser.add_argument("--verify-hash", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate metadata structure without requiring artifact hash verification")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    metadata = load_model_metadata(args.metadata, verify_hash=(args.verify_hash and not args.dry_run))
    print(json.dumps({
        "ok": True,
        "mode": "dry-run" if args.dry_run else "check",
        "name": metadata.name,
        "role": metadata.role,
        "backend": metadata.backend,
        "artifact": str(metadata.artifact),
        "input_shape": list(metadata.input_shape),
        "outputs": list(metadata.output_names),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
