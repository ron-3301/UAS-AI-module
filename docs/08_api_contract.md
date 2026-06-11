# DOCUMENT 8: API & TELEMETRY CONTRACT (For UAS Integrators)

## 1. Input – Telemetry Stream (MAVLink 2.0)

The AI module subscribes to UDP port 14550 (configurable). Required messages:

| MAVLink Message          | Fields Used                                      | Frequency |
|--------------------------|--------------------------------------------------|-----------|
| `GLOBAL_POSITION_INT`    | lat, lon, alt (MSL), relative_alt (AGL)         | 10 Hz     |
| `ATTITUDE`               | roll, pitch, yaw                                 | 10 Hz     |
| `VFR_HUD`                | groundspeed, heading                             | 5 Hz      |
| `TIMESTAMP`              | time_boot_ms (for sync)                          | 20 Hz     |

All fields are SI units (degrees, metres, m/s). The module tolerates missing messages up to 1 second.

## 2. Output – Targeting Packet (JSON over UDP)

Destination IP and port set in `inference.yaml` (default: 192.168.1.255:5005, broadcast).  
Packet schema as per master document Section 11. Example:

```json
{
  "schema_version": "1.0",
  "mission_id": "MSN-20240615-001",
  "frame_id": 4821,
  "timestamp_utc": "2024-06-15T09:32:14.823Z",
  "uas_telemetry": { "lat": 51.5074, "lon": -0.1278, "alt_agl_m": 98.7 },
  "detections": [
    {
      "detection_id": "d_4821_001",
      "track_id": 17,
      "bbox_px": [842, 391, 964, 447],
      "detection_class": "Vehicle-Wheeled",
      "detection_confidence": 0.91,
      "identification": { "label": "Humvee", "confidence": 0.84 },
      "geolocation": { "lat": 51.507612, "lon": -0.128043, "cep_m": 3.8 },
      "threat_score": 0.73
    }
  ]
}
If no detections, send {"detections": []}.

3. Health Endpoint (HTTP)
The module exposes a simple HTTP endpoint on port 8080 /health returning:

json
{
  "status": "running",
  "uptime_seconds": 1234,
  "fps": 28.3,
  "last_error": null,
  "gpu_memory_used_mb": 1240
}
4. Error Codes (in JSON packet)
When a non‑fatal error occurs, the targeting packet includes an error field:

json
{
  "detections": [],
  "error": { "code": 100, "message": "Camera stream lost" }
}
Codes:

100: Camera stream timeout

101: Telemetry sync lost

102: GPS denied (fallback active)

103: Model inference failed (fallback to CPU)