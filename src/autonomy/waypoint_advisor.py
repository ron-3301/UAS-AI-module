from typing import Dict

class WaypointAdvisor:
    def recommend(self, lat, lon, alt_m, reason="REACQUIRE"):
        return {"command": "SET_POSITION_TARGET_GLOBAL_INT", "lat": lat, "lon": lon, "alt_m": alt_m, "reason": reason}