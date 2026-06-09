# layer 5 - build & emit the targeting JSON packet over UDP/MQTT.
#
# IMPORTANT (DEC-003 / docs/12 §2):
# the civilian-suppression + min-confidence filters in _apply_safety_filters
# are NOT exposed to YAML. Changing them needs a code change + new
# DECISIONS.md entry + review.
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

# ---- safety constants. DO NOT YAML-ify these. ----
MIN_DETECTION_CONF       = 0.30
CIVILIAN_ID_CONF_DROP    = 0.50
MAX_CEP_M_FOR_VALID      = 25.0
MIN_ALT_AGL_FOR_PERSON_M = 30.0
CIVILIAN_LABEL_PREFIX    = "Civilian"
# --------------------------------------------------


@dataclass
class Detection:
    detection_id: str
    track_id: int | None
    bbox_px: tuple[int, int, int, int]
    detection_class: str
    detection_confidence: float
    identification: dict[str, Any] | None = None   # {'label':..., 'confidence':...}
    geolocation: dict[str, Any] | None = None      # {'lat','lon','cep_m'}
    threat_score: float = 0.0


@dataclass
class Packet:
    schema_version: str
    mission_id: str
    frame_id: int
    timestamp_utc: str
    uas_telemetry: dict[str, Any]
    detections: list[Detection] = field(default_factory=list)
    error: dict[str, Any] | None = None
    validity_flag: bool = True
    audit: dict[str, str] | None = None


def _apply_safety_filters(det: Detection, alt_agl_m: float | None) -> tuple[bool, str | None]:
    # returns (keep, reason). reason is None when keep=True.
    if det.detection_confidence < MIN_DETECTION_CONF:
        return False, "below_min_detection_conf"

    if det.identification:
        lbl = str(det.identification.get("label", ""))
        c = float(det.identification.get("confidence", 0.0))
        if lbl.startswith(CIVILIAN_LABEL_PREFIX) and c > CIVILIAN_ID_CONF_DROP:
            return False, "civilian_identified"

    # never call out Person targets at low altitude (bystander risk)
    if (det.detection_class == "Person"
            and alt_agl_m is not None
            and alt_agl_m < MIN_ALT_AGL_FOR_PERSON_M):
        return False, "person_below_min_altitude"

    return True, None


def _enforce_validity(det: Detection, pkt: Packet) -> None:
    if det.geolocation and det.geolocation.get("cep_m", 0.0) > MAX_CEP_M_FOR_VALID:
        pkt.validity_flag = False


def build_packet(
    raw: Packet,
    *,
    alt_agl_m: float | None = None,
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    # apply safety filters + emit the wire dict.
    # returns (packet_dict, suppressed_list) where suppressed_list is
    # (detection_id, reason) pairs for the SQLite audit log.
    kept: list[Detection] = []
    suppressed: list[tuple[str, str]] = []
    for d in raw.detections:
        ok, why = _apply_safety_filters(d, alt_agl_m)
        if ok:
            _enforce_validity(d, raw)
            kept.append(d)
        else:
            suppressed.append((d.detection_id, why or "unknown"))

    out: dict[str, Any] = {
        "schema_version": raw.schema_version,
        "mission_id": raw.mission_id,
        "frame_id": raw.frame_id,
        "timestamp_utc": raw.timestamp_utc,
        "uas_telemetry": raw.uas_telemetry,
        "validity_flag": raw.validity_flag,
        "detections": [
            {
                "detection_id": d.detection_id,
                "track_id": d.track_id,
                "bbox_px": list(d.bbox_px),
                "detection_class": d.detection_class,
                "detection_confidence": round(d.detection_confidence, 3),
                **({"identification": d.identification} if d.identification else {}),
                **({"geolocation": d.geolocation} if d.geolocation else {}),
                "threat_score": round(d.threat_score, 3),
            }
            for d in kept
        ],
    }
    if raw.audit:
        out["audit"] = raw.audit
    if raw.error:
        out["error"] = raw.error
    return out, suppressed


def to_json_bytes(pkt: dict[str, Any]) -> bytes:
    return json.dumps(pkt, separators=(",", ":")).encode("utf-8")
