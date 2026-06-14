"""Model export-plan parsing and validation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPORT_PLAN_SCHEMA = PROJECT_ROOT / "schemas" / "models" / "export_plan.schema.json"


class ExportPlanError(ValueError):
    """Raised when a model export plan is invalid."""


@dataclass(frozen=True)
class ExportArtifact:
    name: str
    role: str
    source_checkpoint: Path
    onnx_output: Path
    metadata_output: Path
    tensorrt_output: Path | None
    input_shape: tuple[int, ...]
    class_names: tuple[str, ...]


@dataclass(frozen=True)
class ExportPlan:
    version: str
    plan_id: str
    artifacts: tuple[ExportArtifact, ...]


def load_export_plan(path: str | Path, *, validate_checkpoint_exists: bool = False) -> ExportPlan:
    plan_path = Path(path)
    data = json.loads(plan_path.read_text())
    _validate_schema_if_available(data)
    artifacts = tuple(
        _parse_artifact(item, base_dir=plan_path.parent, validate_checkpoint_exists=validate_checkpoint_exists)
        for item in data["artifacts"]
    )
    names = [artifact.name for artifact in artifacts]
    if len(set(names)) != len(names):
        raise ExportPlanError("export artifact names must be unique")
    return ExportPlan(version=str(data["version"]), plan_id=str(data["plan_id"]), artifacts=artifacts)


def export_plan_summary(plan: ExportPlan) -> dict[str, Any]:
    return {
        "version": plan.version,
        "plan_id": plan.plan_id,
        "artifacts": [
            {
                "name": artifact.name,
                "role": artifact.role,
                "source_checkpoint": str(artifact.source_checkpoint),
                "onnx_output": str(artifact.onnx_output),
                "metadata_output": str(artifact.metadata_output),
                "tensorrt_output": str(artifact.tensorrt_output) if artifact.tensorrt_output else None,
                "input_shape": list(artifact.input_shape),
                "class_names": list(artifact.class_names),
            }
            for artifact in plan.artifacts
        ],
    }


def _parse_artifact(item: dict[str, Any], *, base_dir: Path, validate_checkpoint_exists: bool) -> ExportArtifact:
    source_checkpoint = _resolve(base_dir, item["source_checkpoint"])
    onnx_output = _resolve(base_dir, item["onnx_output"])
    metadata_output = _resolve(base_dir, item["metadata_output"])
    tensorrt_output = _resolve(base_dir, item["tensorrt_output"]) if item.get("tensorrt_output") else None

    if source_checkpoint.suffix.lower() not in {".pt", ".pth", ".ckpt"}:
        raise ExportPlanError("source_checkpoint must be a training checkpoint (.pt/.pth/.ckpt)")
    if onnx_output.suffix.lower() != ".onnx":
        raise ExportPlanError("onnx_output must end with .onnx")
    if metadata_output.suffix.lower() != ".json":
        raise ExportPlanError("metadata_output must end with .json")
    if tensorrt_output and tensorrt_output.suffix.lower() != ".engine":
        raise ExportPlanError("tensorrt_output must end with .engine")
    if validate_checkpoint_exists and not source_checkpoint.exists():
        raise ExportPlanError(f"source checkpoint not found: {source_checkpoint}")

    return ExportArtifact(
        name=str(item["name"]),
        role=str(item["role"]),
        source_checkpoint=source_checkpoint,
        onnx_output=onnx_output,
        metadata_output=metadata_output,
        tensorrt_output=tensorrt_output,
        input_shape=tuple(int(value) for value in item["input_shape"]),
        class_names=tuple(str(value) for value in item.get("class_names", [])),
    )


def _resolve(base_dir: Path, value: str) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (base_dir / path).resolve()


def _validate_schema_if_available(data: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return
    schema = json.loads(EXPORT_PLAN_SCHEMA.read_text())
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        messages = []
        for error in errors:
            location = "/".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        raise ExportPlanError("export plan schema validation failed:\n- " + "\n- ".join(messages))
