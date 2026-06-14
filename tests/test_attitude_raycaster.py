from __future__ import annotations

from datetime import datetime, timezone

import pytest

from uas_ai_module.geolocation.attitude_raycaster import AttitudeAwareGroundPlaneRaycaster
from uas_ai_module.models import CameraIntrinsics, Detection, Frame, Telemetry


def make_raycaster() -> AttitudeAwareGroundPlaneRaycaster:
    return AttitudeAwareGroundPlaneRaycaster(CameraIntrinsics("cam", 640, 480, 640.0, 640.0, 320.0, 240.0))


def make_frame() -> Frame:
    return Frame("f", datetime.now(timezone.utc), 640, 480, data=None)


def make_telemetry(**kwargs) -> Telemetry:
    values = dict(
        timestamp_utc=datetime.now(timezone.utc),
        lat_deg=28.0,
        lon_deg=77.0,
        alt_msl_m=300.0,
        alt_agl_m=100.0,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=0.0,
    )
    values.update(kwargs)
    return Telemetry(**values)


def test_attitude_raycaster_center_pixel_under_zero_attitude() -> None:
    point = make_raycaster().geolocate(
        Detection("Vehicle-Wheeled", 0.9, (310, 230, 330, 250)),
        make_frame(),
        make_telemetry(),
    )
    assert point.valid is True
    assert point.lat_deg == pytest.approx(28.0, abs=1e-6)
    assert point.lon_deg == pytest.approx(77.0, abs=1e-6)


def test_attitude_raycaster_right_pixel_moves_east() -> None:
    point = make_raycaster().geolocate(
        Detection("Vehicle-Wheeled", 0.9, (420, 230, 440, 250)),
        make_frame(),
        make_telemetry(),
    )
    assert point.valid is True
    assert point.lon_deg is not None and point.lon_deg > 77.0


def test_attitude_raycaster_large_pitch_can_fail_closed() -> None:
    point = make_raycaster().geolocate(
        Detection("Vehicle-Wheeled", 0.9, (310, 230, 330, 250)),
        make_frame(),
        make_telemetry(pitch_deg=100.0),
    )
    assert point.valid is False
    assert point.reason == "ray_does_not_intersect_ground"
