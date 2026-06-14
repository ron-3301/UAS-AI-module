#!/usr/bin/env python3
"""Guard Jetson runtime requirements against forbidden dependencies."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REQ = ROOT / "requirements" / "requirements-runtime.txt"
UPLOADED_REQ = ROOT / "requirements" / "requirements-uploaded.txt"

FORBIDDEN_RUNTIME = {
    "torch",
    "torchvision",
    "torchaudio",
    "ultralytics",  # training/export only; not Jetson runtime
}


def normalize_package_name(line: str) -> str | None:
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    line = line.split(";", 1)[0].strip()
    match = re.match(r"([A-Za-z0-9_.-]+)", line)
    if not match:
        return None
    return match.group(1).lower().replace("_", "-")


def packages(path: Path) -> set[str]:
    return {pkg for line in path.read_text().splitlines() if (pkg := normalize_package_name(line))}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check runtime requirements for forbidden packages")
    parser.add_argument("--requirements", default=str(RUNTIME_REQ), help="Runtime requirements file to inspect")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    req_path = Path(args.requirements)
    runtime = packages(req_path)
    forbidden = sorted(runtime & FORBIDDEN_RUNTIME)
    if forbidden:
        print(f"Forbidden runtime dependencies in {req_path.relative_to(ROOT)}: {forbidden}", file=sys.stderr)
        return 1

    print(f"Runtime dependency guard passed for {req_path.relative_to(ROOT)}")

    if UPLOADED_REQ.exists() and req_path.resolve() == RUNTIME_REQ.resolve():
        uploaded = packages(UPLOADED_REQ)
        uploaded_forbidden = sorted(uploaded & FORBIDDEN_RUNTIME)
        if uploaded_forbidden:
            print(
                "Note: original uploaded combined requirements contain training-only/forbidden-runtime packages: "
                f"{uploaded_forbidden}. Keep them out of Jetson runtime images."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
