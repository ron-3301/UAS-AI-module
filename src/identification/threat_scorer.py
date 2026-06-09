# threat_score per docs/11 §2:
#   score = clip(w_class * f_det * f_id * f_prox * f_motion * f_context, 0, 1)
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ThreatInputs:
    detection_class: str
    detection_conf: float
    id_label: str | None
    id_conf: float | None
    slant_range_m: float
    speed_mps: float = 0.0
    static_seconds: float = 0.0
    context_multiplier: float = 1.0


class ThreatScorer:
    def __init__(self, weights_path: str | Path) -> None:
        with open(weights_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.class_weights: dict[str, float] = cfg["weights"]
        self.overrides: dict[str, float] = cfg.get("overrides", {})

    def score(self, t: ThreatInputs) -> float:
        # per-class baseline, but a matched sub-label overrides it
        w = self.class_weights.get(t.detection_class, 0.0)
        if t.id_label and t.id_label in self.overrides:
            w = self.overrides[t.id_label]

        f_det  = max(0.1, min(1.0, t.detection_conf))
        f_id   = 1.0 if t.id_conf is None else 0.5 + 0.5 * max(0.0, min(1.0, t.id_conf))
        f_prox = 1.0 - min(0.7, max(0.0, t.slant_range_m / 500.0))

        # motion bump if it's moving, penalty if it's been static a while
        if t.speed_mps > 5.0:
            f_motion = 1.2
        elif t.static_seconds > 30.0:
            f_motion = 0.7
        else:
            f_motion = 1.0

        f_ctx = max(0.5, min(1.5, t.context_multiplier))

        raw = w * f_det * f_id * f_prox * f_motion * f_ctx
        return max(0.0, min(1.0, raw))


def from_config(class_weights_yaml: str | Path) -> ThreatScorer:
    return ThreatScorer(class_weights_yaml)
