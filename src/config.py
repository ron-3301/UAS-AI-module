# config loader. json-schema validation + env/CLI overrides.
#
# precedence (highest first):
#   --override key=value   (CLI, repeatable)
#   UAS_* env vars
#   YAML file
#   built-in defaults below
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).parent.parent / "configs" / "schemas"

# fallbacks (lowest precedence)
DEFAULTS: dict[str, Any] = {
    "log_level": "INFO",
    "log_dir": "logs/",
    "mission_profile": "tracking",
}

ENV_PREFIX = "UAS_"


def _deep_set(d: dict[str, Any], dotted: str, val: Any) -> None:
    parts = dotted.split(".")
    cur = d
    for k in parts[:-1]:
        cur = cur.setdefault(k, {})
    cur[parts[-1]] = _coerce(val)


def _coerce(s: Any) -> Any:
    # env/CLI vals come in as strings; best-effort cast back to bool/int/float.
    if not isinstance(s, str):
        return s
    low = s.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _apply_env_overrides(cfg: dict[str, Any]) -> None:
    for k, v in os.environ.items():
        if not k.startswith(ENV_PREFIX):
            continue
        dotted = k[len(ENV_PREFIX):].lower().replace("__", ".")
        _deep_set(cfg, dotted, v)


def _apply_cli_overrides(cfg: dict[str, Any], items: list[str]) -> None:
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"--override must be KEY=VALUE, got: {raw!r}")
        k, v = raw.split("=", 1)
        _deep_set(cfg, k, v)


def load_and_validate(path: Path, overrides: list[str] | None = None) -> dict[str, Any]:
    overrides = overrides or []
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # fill missing top-level keys with defaults
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)

    _apply_env_overrides(cfg)
    _apply_cli_overrides(cfg, overrides)

    # schema validate (matched by file stem)
    schema_path = SCHEMA_DIR / f"{path.stem}.schema.json"
    if schema_path.exists():
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        v = Draft7Validator(schema)
        errs = sorted(v.iter_errors(cfg), key=lambda e: e.path)
        if errs:
            joined = "\n".join(
                f"  - {'.'.join(map(str, e.path))}: {e.message}" for e in errs
            )
            raise ValueError(f"Config {path} failed validation:\n{joined}")

    # major-version compat check (see doc 6 §3)
    if "version" in cfg:
        major = cfg["version"].partition(".")[0]
        if major != "1":
            raise ValueError(f"Unsupported config major version: {cfg['version']}")

    return cfg
