from typing import Dict, Any

class TelemetryParser:
    def __init__(self):
        self.last = {"lat": 0.0, "lon": 0.0, "alt_agl_m": 100.0}

    def parse(self, mavlink_msg: Dict[str, Any]) -> Dict[str, Any]:
        return self.last
