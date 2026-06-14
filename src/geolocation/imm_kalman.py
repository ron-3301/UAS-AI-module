import numpy as np
from typing import Dict

class IMMKalman:
    def __init__(self):
        self.models = ["CV", "CT", "Braking"]
        self.prob = np.array([0.6, 0.2, 0.2])
        self.x = np.zeros(4)

    def predict(self):
        return {"model": self.models[np.argmax(self.prob)], "probability": float(np.max(self.prob))}

    def update(self, measurement):
        self.x = 0.8 * self.x + 0.2 * np.array([measurement["lat"], measurement["lon"], 0, 0])
        self.prob = np.array([0.5, 0.3, 0.2])
        return self.predict()