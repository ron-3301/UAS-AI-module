# every shipped yaml must validate against its json schema (when one exists).
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

REPO = Path(__file__).resolve().parents[2]
CFG_DIR = REPO / "configs"
SCHEMA_DIR = CFG_DIR / "schemas"


def _pairs():
    for cfg in sorted(CFG_DIR.glob("*.yaml")):
        schema = SCHEMA_DIR / f"{cfg.stem}.schema.json"
        if schema.exists():
            yield pytest.param(cfg, schema, id=cfg.name)


@pytest.mark.parametrize("cfg_path, schema_path", list(_pairs()))
def test_config_validates(cfg_path: Path, schema_path: Path) -> None:
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)
    errors = sorted(Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    assert not errors, "\n".join(
        f"{'.'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
    )


def test_every_yaml_has_a_schema() -> None:
    # forces us to add a schema whenever we add a new config — catches drift.
    yamls = {p.stem for p in CFG_DIR.glob("*.yaml")}
    schemas = {p.stem.replace(".schema", "") for p in SCHEMA_DIR.glob("*.schema.json")}
    missing = yamls - schemas
    assert not missing, f"Missing JSON schemas for: {sorted(missing)}"
