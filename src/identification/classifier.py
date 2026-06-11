from typing import List, Dict, Any
import numpy as np

class MockClassifier:
    def __init__(self):
        self.labels = ["Civilian-Sedan", "Humvee", "Civilian-Person"]

    def predict(self, crops: List[np.ndarray]) -> List[Dict[str, Any]]:
        results = []
        for _ in crops:
            results.append({
                "label": "Civilian-Sedan",
                "confidence": 0.78,
                "is_civilian": True
            })
        return results
