from __future__ import annotations

from datetime import datetime, timezone

from uas_ai_module.geolocation.raycaster import GroundPlaneRaycaster
from uas_ai_module.models import CameraIntrinsics, Detection, Frame, Telemetry
from uas_ai_module.prediction.tcpa import compute_tcpa


def test_raycaster_center_pixel_stays_near_ownship_ground_point() -> None:
    intrinsics = CameraIntrinsics("cam", 640, 480, 640.0, 640.0, 320.0, 240.0)
    raycaster = GroundPlaneRaycaster(intrinsics)
    frame = Frame("f", datetime.now(timezone.utc), 640, 480, data=None)
    telemetry = Telemetry(
        timestamp_utc=datetime.now(timezone.utc),
        lat_deg=28.0,
        lon_deg=77.0,
        alt_msl_m=300.0,
        alt_agl_m=100.0,
    )
    detection = Detection("Vehicle-Wheeled", 0.9, (310.0, 230.0, 330.0, 250.0))
    point = raycaster.geolocate(detection, frame, telemetry)
    assert point.valid is True
    assert point.lat_deg is not None and abs(point.lat_deg - telemetry.lat_deg) < 1e-6
    assert point.lon_deg is not None and abs(point.lon_deg - telemetry.lon_deg) < 1e-6
    assert point.cep_m is not None and point.cep_m > 0


def test_raycaster_fails_closed_without_agl() -> None:
    intrinsics = CameraIntrinsics("cam", 640, 480, 640.0, 640.0, 320.0, 240.0)
    raycaster = GroundPlaneRaycaster(intrinsics)
    frame = Frame("f", datetime.now(timezone.utc), 640, 480, data=None)
    telemetry = Telemetry(
        timestamp_utc=datetime.now(timezone.utc),
        lat_deg=28.0,
        lon_deg=77.0,
        alt_msl_m=300.0,
        alt_agl_m=None,
    )
    detection = Detection("Vehicle-Wheeled", 0.9, (310.0, 230.0, 330.0, 250.0))
    point = raycaster.geolocate(detection, frame, telemetry)
    assert point.valid is False
    assert point.reason == "missing_or_invalid_agl"


def test_tcpa_converging_case() -> None:
    result = compute_tcpa((100.0, 0.0), (-10.0, 0.0))
    assert result.is_converging is True
    assert result.tcpa_s == 10.0
    assert result.closest_approach_m == 0.0


def test_tcpa_diverging_case() -> None:
    result = compute_tcpa((100.0, 0.0), (10.0, 0.0))
    assert result.is_converging is False
    assert result.tcpa_s == 0.0
    assert result.closest_approach_m == 100.0
