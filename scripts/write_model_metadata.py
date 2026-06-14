#!/usr/bin/env python3
"""Write a model metadata sidecar from an export plan artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uas_ai_module.data.export_plan import load_export_plan  # noqa: E402


def sha256_or_placeholder(path: Path, *, require_artifact: bool) -> str:
    if not path.exists():
        if require_artifact:
            raise FileNotFoundError(path)
        return "0" * 64
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write model metadata sidecar from export plan")
    parser.add_argument("plan")
    parser.add_argument("--artifact-name", help="Artifact name to export; defaults to first artifact")
    parser.add_argument("--output", help="Override metadata output path")
    parser.add_argument("--require-artifact", action="store_true", help="Require ONNX artifact to exist and hash it")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan = load_export_plan(args.plan)
    artifact = next((item for item in plan.artifacts if item.name == args.artifact_name), plan.artifacts[0])
    metadata = {
        "name": artifact.name,
        "role": artifact.role,
        "artifact": str(artifact.onnx_output),
        "sha256": sha256_or_placeholder(artifact.onnx_output, require_artifact=args.require_artifact and not args.dry_run),
        "backend": "onnxruntime",
        "input": {"name": "images", "shape": list(artifact.input_shape), "dtype": "float32"},
        "outputs": [{"name": "output0"}],
        "class_names": list(artifact.class_names),
        "preprocessing": {"scale": 1.0 / 255.0},
        "export": {"plan_id": plan.plan_id, "source_checkpoint": str(artifact.source_checkpoint)},
    }
    output = Path(args.output) if args.output else artifact.metadata_output
    if args.dry_run:
        print(json.dumps({"ok": True, "mode": "dry-run", "output": str(output), "name": artifact.name}, sort_keys=True))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"ok": True, "output": str(output), "name": artifact.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
