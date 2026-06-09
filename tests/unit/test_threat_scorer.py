# locks the threat-score formula (docs/11 §2) + the worked example (§2.1).
from __future__ import annotations

from pathlib import Path

import pytest

from src.identification.threat_scorer import ThreatInputs, ThreatScorer

REPO = Path(__file__).resolve().parents[2]
WEIGHTS = REPO / "configs" / "class_weights.yaml"


@pytest.fixture(scope="module")
def scorer() -> ThreatScorer:
    return ThreatScorer(WEIGHTS)


def test_humvee_worked_example(scorer: ThreatScorer) -> None:
    # reproduces the worked example from docs/11 §2.1
    t = ThreatInputs(
        detection_class="Vehicle-Wheeled",
        detection_conf=0.91,
        id_label="Humvee",
        id_conf=0.84,
        slant_range_m=120.0,
        speed_mps=7.0,
    )
    # Humvee override = 0.85:
    #   0.85 * 0.91 * (0.5 + 0.5*0.84) * (1 - 120/500) * 1.2 * 1.0
    # = 0.85 * 0.91 * 0.92 * 0.76 * 1.2 = 0.649
    assert scorer.score(t) == pytest.approx(0.649, abs=0.005)


def test_civilian_override_dominates(scorer: ThreatScorer) -> None:
    t = ThreatInputs(
        detection_class="Vehicle-Wheeled",
        detection_conf=0.95,
        id_label="Civilian",
        id_conf=0.9,
        slant_range_m=50.0,
    )
    # Civilian override = 0.05 -> score tiny
    assert scorer.score(t) < 0.10


def test_clipping(scorer: ThreatScorer) -> None:
    # push every factor up - product would exceed 1 without clipping
    t = ThreatInputs(
        detection_class="Vehicle-Tracked",
        detection_conf=1.0,
        id_label="T-90",
        id_conf=1.0,
        slant_range_m=0.0,
        speed_mps=10.0,
        context_multiplier=1.5,
    )
    s = scorer.score(t)
    assert 0.0 <= s <= 1.0


def test_static_target_penalised(scorer: ThreatScorer) -> None:
    base = ThreatInputs(
        detection_class="Vehicle-Wheeled",
        detection_conf=0.9, id_label=None, id_conf=None,
        slant_range_m=100.0, speed_mps=0.0,
    )
    moving = ThreatInputs(**{**base.__dict__, "speed_mps": 8.0})
    static = ThreatInputs(**{**base.__dict__, "static_seconds": 60.0})
    assert scorer.score(moving) > scorer.score(base) > scorer.score(static)
