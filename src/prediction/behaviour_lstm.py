from typing import Tuple, List
import numpy as np

class BehaviourLSTM:
    def predict(self, history):
        maneuvers = ["STOP", "TURN", "APPROACH", "EVADE", "RANDOM"]
        return "APPROACH", 0.78, [0.1, 0.2, 0.4, 0.2, 0.1]