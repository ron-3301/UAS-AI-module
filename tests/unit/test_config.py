# config loader: precedence and schema validation (docs/06_config_management.md).
from __future__ import annotations

from pathlib import Path

import pytest

from src.config import load_and_validate

REPO = Path(__file__).resolve().parents[2]


def test_inference_yaml_valid() -> None:
    cfg = load_and_validate(REPO / "configs" / "inference.yaml")
    assert cfg["model"]["detection_conf_threshold"] == 0.45
    assert cfg["telemetry"]["udp_port"] == 14550


def test_cli_override_wins(tmp_path: Path) -> None:
    cfg = load_and_validate(
        REPO / "configs" / "inference.yaml",
        overrides=["model.detection_conf_threshold=0.7"],
    )
    assert cfg["model"]["detection_conf_threshold"] == 0.7


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAS_MODEL__DETECTION_CONF_THRESHOLD", "0.55")
    cfg = load_and_validate(REPO / "configs" / "inference.yaml")
    assert cfg["model"]["detection_conf_threshold"] == 0.55


def test_cli_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UAS_MODEL__DETECTION_CONF_THRESHOLD", "0.55")
    cfg = load_and_validate(
        REPO / "configs" / "inference.yaml",
        overrides=["model.detection_conf_threshold=0.66"],
    )
    assert cfg["model"]["detection_conf_threshold"] == 0.66


def test_invalid_value_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="detection_conf_threshold"):
        load_and_validate(
            REPO / "configs" / "inference.yaml",
            overrides=["model.detection_conf_threshold=1.5"],
        )
