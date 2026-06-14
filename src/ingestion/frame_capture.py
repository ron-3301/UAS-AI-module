from typing import Optional
import numpy as np
class FrameCapture:
    def __init__(self, source: str = "mock"):
        self.source = source; self.frame_id = 0
    def read(self) -> Optional[np.ndarray]:
        if self.source == "mock":
            self.frame_id += 1
            return np.zeros((480, 640, 3), dtype=np.uint8)
        raise NotImplementedError("Real camera not implemented")