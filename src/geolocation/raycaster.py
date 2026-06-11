from typing import Dict, Any

def estimate_geolocation(det: Dict, telemetry: Dict, intrinsics: Dict) -> Dict[str, float]:
    lat = telemetry.get("lat", 0.0) + 0.0001
    lon = telemetry.get("lon", 0.0) + 0.0001
    return {"lat": lat, "lon": lon, "cep_m": 4.2}
