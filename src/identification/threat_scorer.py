from typing import Dict, Any
def compute_threat(det, id_result, intent="RANDOM"):
    base = det.get("confidence", 0.5) * id_result.get("confidence", 0.5)
    intent_mult = {"APPROACH": 1.4, "EVADE": 0.6, "STOP": 0.8, "TURN": 1.0, "RANDOM": 1.0}.get(intent, 1.0)
    return min(max(base * intent_mult, 0.0), 1.0)