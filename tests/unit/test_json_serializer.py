import pytest
from src.output.json_serializer import serialize, MIN_DET_CONF, CIVILIAN_ID_CONF

def test_civilian_suppression():
    packet = serialize("MSN-001", 1, {"alt_agl_m": 100},
        [{"bbox": [0,0,10,10], "class_name": "Vehicle-Wheeled", "confidence": 0.9}],
        [{"label": "Civilian-Sedan", "confidence": 0.7, "is_civilian": True}],
        [{"lat": 0, "lon": 0, "cep_m": 3}], [0.6])
    assert len(packet["detections"]) == 0