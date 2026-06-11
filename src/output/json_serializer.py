from typing import List, Dict, Any
from datetime import datetime, timezone
import hashlib

MIN_DET_CONF = 0.30
CIVILIAN_ID_CONF = 0.50
PERSON_MIN_ALT_AGL = 30.0
MAX_CEP_M = 25.0

def serialize(
    mission_id: str,
    frame_id: int,
    telemetry: Dict,
    detections: List[Dict],
    id_results: List[Dict],
    geo_results: List[Dict],
    threat_scores: List[float]
) -> Dict[str, Any]:
    packet = {
        "schema_version": "1.0",
        "mission_id": mission_id,
        "frame_id": frame_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "uas_telemetry": telemetry,
        "validity_flag": True,
        "detections": [],
        "error": None
    }

    kept = []
    for i, det in enumerate(detections):
        if det["confidence"] < MIN_DET_CONF:
            continue
        id_res = id_results[i] if i < len(id_results) else {}
        geo = geo_results[i] if i < len(geo_results) else {}
        threat = threat_scores[i] if i < len(threat_scores) else 0.0

        if id_res.get("is_civilian") and id_res.get("confidence", 0) > CIVILIAN_ID_CONF:
            continue
        if det.get("class_name") == "Person" and telemetry.get("alt_agl_m", 100) < PERSON_MIN_ALT_AGL:
            continue
        cep = geo.get("cep_m", 0)
        validity = cep <= MAX_CEP_M

        kept.append({
            "detection_id": f"d_{frame_id}_{i:03d}",
            "track_id": det.get("track_id"),
            "bbox_px": det["bbox"],
            "detection_class": det["class_name"],
            "detection_confidence": round(det["confidence"], 3),
            "identification": {
                "label": id_res.get("label", "unknown"),
                "confidence": round(id_res.get("confidence", 0.0), 3)
            },
            "geolocation": geo,
            "threat_score": round(threat, 3),
            "validity_flag": validity
        })

    packet["detections"] = kept
    if not kept and any(d["confidence"] < MIN_DET_CONF for d in detections):
        packet["validity_flag"] = False
        packet["error"] = {"code": 103, "message": "All detections below confidence floor"}

    packet["audit"] = {
        "detector_sha": "mock-detector-v1",
        "classifier_sha": "mock-classifier-v1",
        "dataset_version": "v0.0-mock",
        "config_sha": hashlib.sha256(b"dev").hexdigest()[:8],
        "ruleset_version": "safety-v1"
    }
    return packet
