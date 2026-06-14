from __future__ import annotations

import json
from pathlib import Path

import pytest

from uas_ai_module.model_manifest import ModelManifestError, load_model_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_model_manifest_example_loads_without_requiring_files() -> None:
    manifest = load_model_manifest(ROOT / "models" / "manifest.example.json")
    assert manifest.version == "1.0"
    detectors = manifest.by_role("detector")
    assert len(detectors) == 1
    assert detectors[0].backend == "onnxruntime"
    assert detectors[0].path.suffix == ".onnx"


def test_model_manifest_rejects_pt_runtime_artifact(tmp_path: Path) -> None:
    data = json.loads((ROOT / "models" / "manifest.example.json").read_text())
    data["artifacts"][0]["path"] = "bad.pt"
    path = tmp_path / "bad_manifest.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ModelManifestError):
        load_model_manifest(path)


def test_model_manifest_rejects_backend_suffix_mismatch(tmp_path: Path) -> None:
    data = json.loads((ROOT / "models" / "manifest.example.json").read_text())
    data["artifacts"][0]["path"] = "detector.engine"
    data["artifacts"][0]["backend"] = "onnxruntime"
    path = tmp_path / "bad_manifest.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ModelManifestError, match="onnxruntime"):
        load_model_manifest(path)
