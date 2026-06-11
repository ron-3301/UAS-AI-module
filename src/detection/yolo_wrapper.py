from typing import List, Dict, Any
import numpy as np

class MockDetector:
    CLASSES = ["Person", "Vehicle-Wheeled", "Vehicle-Tracked",
               "Aircraft-Rotary", "Aircraft-Fixed", "Watercraft", "Structure-Temp"]

    def __init__(self, conf_threshold: float = 0.3):
        self.conf_threshold = conf_threshold

    def predict(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        h, w = frame.shape[:2]
        return [{
            "bbox": [w//4, h//4, w//2, h//2],
            "class_id": 1,
            "class_name": "Vehicle-Wheeled",
            "confidence": 0.85,
            "track_id": None
        }]

    def update(self, detections: List[Dict]) -> List[Dict]:
        for d in detections:
            d["track_id"] = 17
        return detections
