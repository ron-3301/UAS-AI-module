from typing import Dict

class SpoofDetector:
    def __init__(self, threshold_m=50.0):
        self.threshold_m = threshold_m
        self.last_gps = None
        self.consecutive_spoofs = 0

    def update(self, gps, vo_delta):
        if self.last_gps is None:
            self.last_gps = gps
            return False
        dlat = abs(gps["lat"] - self.last_gps["lat"])
        dlon = abs(gps["lon"] - self.last_gps["lon"])
        gps_delta_m = (dlat + dlon) * 111000
        vo_delta_m = (vo_delta.get("lat", 0) + vo_delta.get("lon", 0)) * 111000
        if abs(gps_delta_m - vo_delta_m) > self.threshold_m:
            self.consecutive_spoofs += 1
        else:
            self.consecutive_spoofs = 0
        self.last_gps = gps
        return self.consecutive_spoofs >= 3