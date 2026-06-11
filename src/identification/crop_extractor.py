from typing import List, Dict, Any
import numpy as np

def extract_crops(frame: np.ndarray, detections: List[Dict]) -> List[np.ndarray]:
    crops = []
    for det in detections:
        x, y, w, h = det["bbox"]
        crop = frame[y:y+h, x:x+w]
        if crop.size > 0:
            crops.append(crop)
    return crops
