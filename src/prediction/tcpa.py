import math
from typing import Dict

def compute_tcpa(ownship, target, horizon=30.0):
    rel_lat = target["lat"] - ownship["lat"]
    rel_lon = target["lon"] - ownship["lon"]
    rel_speed = math.sqrt(rel_lat**2 + rel_lon**2)
    if rel_speed < 1e-6:
        return {"tcpa_s": 999.0, "closest_distance_m": 0.0}
    tcpa = min(horizon, rel_speed / 0.0001)
    closest = rel_speed * 111000
    return {"tcpa_s": round(tcpa, 1), "closest_distance_m": round(closest, 1)}