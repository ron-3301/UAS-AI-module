from __future__ import annotations

import json
from pathlib import Path

import pytest

from uas_ai_module.config import ConfigError, load_config
from uas_ai_module.detection.detector import RuntimeModelConfigError, validate_runtime_model_path

ROOT = Path(__file__).resolve().parents[1]


def test_example_inference_config_loads() -> None:
    config = load_config(ROOT / "configs" / "inference.example.json")
    assert config["model"]["detection_weights"].endswith(".onnx")


def test_runtime_config_rejects_pt_weights(tmp_path: Path) -> None:
    config = json.loads((ROOT / "configs" / "inference.example.json").read_text())
    config["model"]["detection_weights"] = "models/bad.pt"
    path = tmp_path / "bad_config.json"
    path.write_text(json.dumps(config))

    with pytest.raises(ConfigError, match="must not use .pt"):
        load_config(path)


def test_runtime_model_path_accepts_onnx_and_engine() -> None:
    assert validate_runtime_model_path("model.onnx").suffix == ".onnx"
    assert validate_runtime_model_path("model.engine").suffix == ".engine"


def test_runtime_model_path_rejects_pt() -> None:
    with pytest.raises(RuntimeModelConfigError):
        validate_runtime_model_path("model.pt")
