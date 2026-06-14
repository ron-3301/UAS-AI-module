from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from uas_ai_module.model_manifest import ModelManifestError, load_model_manifest
from uas_ai_module.model_metadata import ModelMetadataError, load_model_metadata, sha256_file


def test_model_metadata_verifies_hash(tmp_path: Path) -> None:
    artifact = tmp_path / "detector.onnx"
    artifact.write_bytes(b"fake-onnx")
    digest = hashlib.sha256(b"fake-onnx").hexdigest()
    metadata = {
        "name": "detector-test",
        "role": "detector",
        "artifact": "detector.onnx",
        "sha256": digest,
        "backend": "onnxruntime",
        "input": {"name": "images", "shape": [1, 3, 640, 640], "dtype": "float32"},
        "outputs": [{"name": "output0"}],
        "class_names": ["Vehicle-Wheeled"]
    }
    path = tmp_path / "detector.metadata.json"
    path.write_text(json.dumps(metadata))
    loaded = load_model_metadata(path, verify_hash=True)
    assert loaded.name == "detector-test"
    assert loaded.artifact == artifact
    assert sha256_file(artifact) == digest


def test_model_metadata_rejects_hash_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "detector.onnx"
    artifact.write_bytes(b"fake-onnx")
    metadata = {
        "name": "detector-test",
        "role": "detector",
        "artifact": "detector.onnx",
        "sha256": "0" * 64,
        "backend": "onnxruntime",
        "input": {"name": "images", "shape": [1, 3, 640, 640], "dtype": "float32"},
        "outputs": [{"name": "output0"}]
    }
    path = tmp_path / "detector.metadata.json"
    path.write_text(json.dumps(metadata))
    with pytest.raises(ModelMetadataError, match="sha256 mismatch"):
        load_model_metadata(path, verify_hash=True)


def test_model_manifest_validate_files_exist_checks_hash(tmp_path: Path) -> None:
    artifact = tmp_path / "detector.onnx"
    artifact.write_bytes(b"artifact")
    digest = hashlib.sha256(b"artifact").hexdigest()
    manifest = {
        "version": "1.0",
        "artifacts": [
            {
                "name": "detector-test",
                "role": "detector",
                "path": "detector.onnx",
                "backend": "onnxruntime",
                "sha256": digest,
                "input_shape": [1, 3, 640, 640]
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    loaded = load_model_manifest(path, validate_files_exist=True)
    assert loaded.artifacts[0].path == artifact

    manifest["artifacts"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ModelManifestError, match="sha256 mismatch"):
        load_model_manifest(path, validate_files_exist=True)
