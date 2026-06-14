from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from uas_ai_module.config import ConfigError, load_config
from uas_ai_module.ingestion.file_source import ImageFileFrameSource, load_image_array

ROOT = Path(__file__).resolve().parents[1]


def test_strict_runtime_schema_rejects_pt_structurally(tmp_path: Path) -> None:
    config = json.loads((ROOT / "configs" / "inference.example.json").read_text())
    config["model"]["detection_weights"] = "models/detector.pt"
    path = tmp_path / "bad_runtime.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ConfigError, match="schema validation failed"):
        load_config(path, "inference_runtime.schema.json")


def test_strict_runtime_schema_rejects_unknown_config_fields(tmp_path: Path) -> None:
    config = json.loads((ROOT / "configs" / "inference.example.json").read_text())
    config["model"]["typo_field"] = 123
    path = tmp_path / "bad_runtime.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ConfigError, match="Additional properties"):
        load_config(path, "inference_runtime.schema.json")


def test_image_file_frame_source_reads_npy_arrays(tmp_path: Path) -> None:
    image = np.full((12, 16, 3), 7, dtype=np.uint8)
    path = tmp_path / "frame001.npy"
    np.save(path, image)
    source = ImageFileFrameSource([path])
    frame = source.read()
    assert frame.frame_id == "frame001"
    assert frame.width == 16
    assert frame.height == 12
    assert frame.data.shape == (12, 16, 3)
    with pytest.raises(EOFError):
        source.read()


def test_load_image_array_converts_float_npy_to_uint8(tmp_path: Path) -> None:
    path = tmp_path / "frame.npy"
    np.save(path, np.full((3, 4), 300.0, dtype=np.float32))
    image = load_image_array(path)
    assert image.dtype == np.uint8
    assert image.shape == (3, 4, 1)
    assert int(image.max()) == 255
