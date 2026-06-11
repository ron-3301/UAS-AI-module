from typing import Dict, Any

def compute_threat(det: Dict[str, Any], id_result: Dict[str, Any]) -> float:
    w_class = 0.3 if not id_result.get("is_civilian", True) else 0.1
    score = w_class * det["confidence"] * id_result.get("confidence", 0.5)
    return min(max(score, 0.0), 1.0)
