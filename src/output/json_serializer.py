from typing import List, Dict, Any
from datetime import datetime, timezone
import hashlib

MIN_DET_CONF = 0.30
CIVILIAN_ID_CONF = 0.50

def serialize(mission_id, frame_id, telemetry, detections, id_results, geo_results, threat_scores, intents=None):
    packet = {"schema_version": "1.1", "mission_id": mission_id, "frame_id": frame_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(), "uas_telemetry": telemetry, "validity_flag": True, "detections": [], "error": None}
    kept = []
    for i, det in enumerate(detections):
        if det["confidence"] < MIN_DET_CONF: continue
        id_res = id_results[i] if i < len(id_results) else {}
        if id_res.get("is_civilian") and id_res.get("confidence", 0) > CIVILIAN_ID_CONF: continue
        kept.append({
            "detection_id": f"d_{frame_id}_{i:03d}",
            "track_id": det.get("track_id"),
            "bbox_px": det["bbox"],
            "detection_class": det["class_name"],
            "detection_confidence": round(det["confidence"], 3),
            "identification": {"label": id_res.get("label", "unknown"), "confidence": round(id_res.get("confidence", 0.0), 3)},
            "geolocation": geo_results[i] if i < len(geo_results) else {},
            "threat_score": round(threat_scores[i], 3) if i < len(threat_scores) else 0.0,
            "intent": intents[i] if intents and i < len(intents) else {}
        })
    packet["detections"] = kept
    packet["audit"] = {"detector_sha": "v1", "ruleset_version": "safety-v1"}
    return packet