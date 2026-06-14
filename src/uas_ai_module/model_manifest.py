"""Model manifest validation for runtime deployment."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uas_ai_module.detection.detector import RuntimeModelConfigError, validate_runtime_model_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_MANIFEST_SCHEMA = PROJECT_ROOT / "schemas" / "models" / "model_manifest.schema.json"


class ModelManifestError(ValueError):
    """Raised when a model manifest is invalid."""


@dataclass(frozen=True)
class ModelArtifact:
    name: str
    role: str
    path: Path
    backend: str
    sha256: str
    input_shape: tuple[int, ...]
    class_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelManifest:
    version: str
    artifacts: tuple[ModelArtifact, ...]

    def by_role(self, role: str) -> tuple[ModelArtifact, ...]:
        return tuple(artifact for artifact in self.artifacts if artifact.role == role)


def load_model_manifest(path: str | Path, *, validate_files_exist: bool = False) -> ModelManifest:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text())
    _validate_schema_if_available(data)
    artifacts = tuple(_parse_artifact(item, base_dir=manifest_path.parent, validate_files_exist=validate_files_exist) for item in data.get("artifacts", []))
    if not artifacts:
        raise ModelManifestError("model manifest must contain at least one artifact")
    return ModelManifest(version=str(data.get("version", "0.0")), artifacts=artifacts)


def _validate_schema_if_available(data: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return
    schema = json.loads(MODEL_MANIFEST_SCHEMA.read_text())
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.path))
    if errors:
        messages = []
        for error in errors:
            location = "/".join(str(part) for part in error.path) or "<root>"
            messages.append(f"{location}: {error.message}")
        raise ModelManifestError("model manifest schema validation failed:\n- " + "\n- ".join(messages))


def _parse_artifact(item: dict[str, Any], *, base_dir: Path, validate_files_exist: bool) -> ModelArtifact:
    raw_path = Path(str(item["path"]))
    artifact_path = raw_path if raw_path.is_absolute() else (base_dir / raw_path)
    try:
        validate_runtime_model_path(artifact_path)
    except RuntimeModelConfigError as exc:
        raise ModelManifestError(str(exc)) from exc

    backend = str(item["backend"])
    suffix = artifact_path.suffix.lower()
    if backend == "onnxruntime" and suffix != ".onnx":
        raise ModelManifestError("onnxruntime artifacts must use .onnx files")
    if backend == "tensorrt" and suffix != ".engine":
        raise ModelManifestError("tensorrt artifacts must use .engine files")
    if validate_files_exist:
        if not artifact_path.exists():
            raise ModelManifestError(f"model artifact file not found: {artifact_path}")
        actual_sha = _sha256_file(artifact_path)
        expected_sha = str(item["sha256"]).lower()
        if actual_sha != expected_sha:
            raise ModelManifestError(
                f"sha256 mismatch for {artifact_path}: expected {expected_sha}, got {actual_sha}"
            )

    return ModelArtifact(
        name=str(item["name"]),
        role=str(item["role"]),
        path=artifact_path,
        backend=backend,
        sha256=str(item["sha256"]),
        input_shape=tuple(int(x) for x in item["input_shape"]),
        class_names=tuple(str(x) for x in item.get("class_names", [])),
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
