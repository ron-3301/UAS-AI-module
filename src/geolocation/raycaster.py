from typing import Dict, Any
def estimate_geolocation(det, telemetry, intrinsics):
    lat = telemetry.get("lat", 0.0) + 0.0001
    lon = telemetry.get("lon", 0.0) + 0.0001
    return {"lat": lat, "lon": lon, "cep_m": 4.2}