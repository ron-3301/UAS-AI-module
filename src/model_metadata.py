from __future__ import annotations

"""Model sidecar metadata validation and hash checking."""


import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from detection.detector import RuntimeModelConfigError, validate_runtime_model_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_METADATA_SCHEMA = PROJECT_ROOT / "schemas" / "models" / "model_metadata.schema.json"


class ModelMetadataError(ValueError):
    """Raised when model metadata is invalid."""


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    role: str
    artifact: Path
    sha256: str
    backend: str
    input_name: str
    input_shape: tuple[int, ...]
    input_dtype: str
    output_names: tuple[str, ...]
    class_names: tuple[str, ...]


def load_model_metadata(path: str | Path, *, verify_hash: bool = False) -> ModelMetadata:
    metadata_path = Path(path)
    data = json.loads(metadata_path.read_text())
    _validate_schema_if_available(data)
    artifact = Path(str(data["artifact"]))
    if not artifact.is_absolute():
        artifact = metadata_path.parent / artifact
    try:
        validate_runtime_model_path(artifact)
    except RuntimeModelConfigError as exc:
        raise ModelMetadataError(str(exc)) from exc

    backend = str(data["backend"])
    if backend == "onnxruntime" and artifact.suffix.lower() != ".onnx":
        raise ModelMetadataError("onnxruntime metadata must reference a .onnx artifact")
    if backend == "tensorrt" and artifact.suffix.lower() != ".engine":
        raise ModelMetadataError("tensorrt metadata must reference a .engine artifact")

    expected_sha = str(data["sha256"]).lower()
    if verify_hash:
        actual_sha = sha256_file(artifact)
        if actual_sha != expected_sha:
            raise ModelMetadataError(f"sha256 mismatch for {artifact}: expected {expected_sha}, got {actual_sha}")

    input_data = data["input"]
    outputs = data["outputs"]
    return ModelMetadata(
        name=str(data["name"]),
        role=str(data["role"]),
        artifact=artifact,
        sha256=expected_sha,
        backend=backend,
        input_name=str(input_data["name"]),
        input_shape=tuple(int(x) for x in input_data["shape"]),
        input_dtype=str(input_data["dtype"]),
        output_names=tuple(str(item["name"]) for item in outputs),
        class_names=tuple(str(x) for x in data.get("class_names", [])),
    )


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_schema_if_available(data: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return
    schema = json.loads(MODEL_METADATA_SCHEMA.read_text())
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        messages = []
        for error in errors:
            location = "/".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        raise ModelMetadataError("model metadata schema validation failed:\n- " + "\n- ".join(messages))
