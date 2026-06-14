import cv2
import numpy as np
from typing import List

def apply_tta(frame: np.ndarray, n_augmentations: int = 3) -> List[np.ndarray]:
    augmentations = [frame]
    h, w = frame.shape[:2]
    if n_augmentations >= 2:
        augmentations.append(cv2.flip(frame, 1))
    for angle in [5, -5]:
        if len(augmentations) >= n_augmentations: break
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1.0)
        augmentations.append(cv2.warpAffine(frame, M, (w, h), borderValue=0))
    return augmentations[:n_augmentations]