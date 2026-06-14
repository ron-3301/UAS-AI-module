"""Configuration loading and validation.

JSON Schema provides structural validation. This module adds semantic checks that
are especially important for the Jetson runtime path, where PyTorch artifacts and
training-only settings must not leak into deployment.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration is structurally or semantically invalid."""


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = PROJECT_ROOT / "schemas"


def _load_text_config(path: Path) -> dict[str, Any]:
    text = path.read_text()
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on environment
            raise ConfigError("PyYAML is required to load YAML config files") from exc
        data = yaml.safe_load(text)
    else:
        raise ConfigError(f"unsupported config extension for {path}: expected .json/.yaml/.yml")

    if not isinstance(data, dict):
        raise ConfigError(f"config root must be an object: {path}")
    return data


def _validate_schema(data: dict[str, Any], schema_path: Path) -> None:
    if not schema_path.exists():
        raise ConfigError(f"schema not found: {schema_path}")

    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on environment
        raise ConfigError("jsonschema is required for config validation") from exc

    schema = json.loads(schema_path.read_text())
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        formatted = []
        for err in errors:
            location = "/".join(str(part) for part in err.path) or "<root>"
            formatted.append(f"{location}: {err.message}")
        raise ConfigError("schema validation failed:\n- " + "\n- ".join(formatted))


def _semantic_validate_inference(data: dict[str, Any], *, runtime: bool) -> None:
    model = data.get("model", {})
    weights = str(model.get("detection_weights", ""))
    if runtime and weights.endswith(".pt"):
        raise ConfigError(
            "runtime inference config must not use .pt weights; export to .onnx or .engine first"
        )

    geolocation = data.get("geolocation", {}) or {}
    terrain_model = geolocation.get("terrain_model")
    dted_path = geolocation.get("dted_path")
    if terrain_model in {"dted1", "dted2"} and not dted_path:
        raise ConfigError(f"geolocation.dted_path is required when terrain_model={terrain_model!r}")

    telemetry = data.get("telemetry", {})
    if telemetry.get("source") == "file" and not telemetry.get("file_path"):
        # Uploaded schema does not include file_path yet, but semantic validation
        # documents the intended stricter behavior.
        raise ConfigError("telemetry.file_path is required when telemetry.source='file'")


def _semantic_validate_training(data: dict[str, Any]) -> None:
    splits = data.get("dataset", {}).get("splits")
    if isinstance(splits, dict):
        total = sum(float(splits.get(name, 0.0)) for name in ("train", "val", "test"))
        if abs(total - 1.0) > 1e-6:
            raise ConfigError(f"dataset.splits must sum to 1.0, got {total:.6f}")


def validate_config(data: dict[str, Any], schema_name: str, *, runtime: bool = True) -> None:
    """Validate a config dictionary against schema and semantic constraints."""

    schema_path = SCHEMA_ROOT / "config" / schema_name
    _validate_schema(data, schema_path)

    if schema_name == "inference.schema.json":
        _semantic_validate_inference(data, runtime=runtime)
    elif schema_name == "training.schema.json":
        _semantic_validate_training(data)


def load_config(path: str | Path, schema_name: str = "inference.schema.json", *, runtime: bool = True) -> dict[str, Any]:
    """Load and validate a JSON/YAML config file."""

    config_path = Path(path)
    data = _load_text_config(config_path)
    validate_config(data, schema_name, runtime=runtime)
    return data


def load_camera_intrinsics(path: str | Path) -> dict[str, Any]:
    """Load and validate a camera intrinsics config."""

    config_path = Path(path)
    data = _load_text_config(config_path)
    validate_config(data, "cam01_intrinsics.schema.json", runtime=True)
    return data
