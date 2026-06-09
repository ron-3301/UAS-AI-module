#!/usr/bin/env python3
# Validate every YAML in configs/ against its JSON schema (if it has one).
# non-zero exit on any failure. used in CI + pre-commit.
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

ROOT       = Path(__file__).resolve().parent.parent
CFG_DIR    = ROOT / "configs"
SCHEMA_DIR = CFG_DIR / "schemas"


def main() -> int:
    fails = 0
    for cfg in sorted(CFG_DIR.glob("*.yaml")):
        schema = SCHEMA_DIR / f"{cfg.stem}.schema.json"
        if not schema.exists():
            print(f"[skip] {cfg.name} (no schema)")
            continue
        with open(cfg, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        with open(schema, encoding="utf-8") as f:
            sch = json.load(f)
        errs = sorted(Draft7Validator(sch).iter_errors(data), key=lambda e: list(e.path))
        if errs:
            fails += 1
            print(f"[FAIL] {cfg.name}")
            for e in errs:
                path = '.'.join(map(str, e.path)) or "<root>"
                print(f"   - {path}: {e.message}")
        else:
            print(f"[ok]   {cfg.name}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
