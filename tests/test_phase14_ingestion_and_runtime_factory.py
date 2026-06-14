from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pytest

from uas_ai_module.ingestion.camera import OpenCvCameraSource
from uas_ai_module.ingestion.mavlink import MavlinkTelemetryError, MavlinkTelemetrySource
from uas_ai_module.runtime_factory import build_frame_source_from_config, build_telemetry_source_from_config


@dataclass
class FakeMessage:
    kind: str
    lat: int | None = None
    lon: int | None = None
    alt: int | None = None
    relative_alt: int | None = None
    vx: int = 0
    vy: int = 0
    vz: int = 0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    def get_type(self) -> str:
        return self.kind


class FakeConnection:
    def __init__(self, messages):
        self.messages = list(messages)

    def recv_match(self, type, blocking, timeout):
        if not self.messages:
            return None
        return self.messages.pop(0)


class FakeCapture:
    def __init__(self, frame=None, opened=True):
        self.frame = frame if frame is not None else np.zeros((12, 16, 3), dtype=np.uint8)
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return True, self.frame

    def release(self):
        self.released = True


def test_mavlink_source_parses_attitude_and_global_position() -> None:
    connection = FakeConnection([
        FakeMessage("ATTITUDE", roll=0.1, pitch=-0.2, yaw=math.pi / 2),
        FakeMessage(
            "GLOBAL_POSITION_INT",
            lat=286139000,
            lon=772090000,
            alt=300000,
            relative_alt=120000,
            vx=123,
            vy=-50,
            vz=10,
        ),
    ])
    source = MavlinkTelemetrySource(connection=connection)
    telemetry = source.read()
    assert telemetry.lat_deg == pytest.approx(28.6139)
    assert telemetry.lon_deg == pytest.approx(77.209)
    assert telemetry.alt_msl_m == pytest.approx(300.0)
    assert telemetry.alt_agl_m == pytest.approx(120.0)
    assert telemetry.roll_deg == pytest.approx(math.degrees(0.1))
    assert telemetry.pitch_deg == pytest.approx(math.degrees(-0.2))
    assert telemetry.yaw_deg == pytest.approx(90.0)
    assert telemetry.velocity_ned_mps == pytest.approx((1.23, -0.5, 0.1))


def test_mavlink_source_times_out_without_global_position() -> None:
    source = MavlinkTelemetrySource(connection=FakeConnection([]), timeout_s=0.01)
    with pytest.raises(MavlinkTelemetryError):
        source.read()


def test_opencv_camera_source_reads_injected_capture() -> None:
    capture = FakeCapture(np.ones((9, 11, 3), dtype=np.uint8))
    source = OpenCvCameraSource(capture=capture, camera_id="unitcam")
    frame = source.read()
    assert frame.frame_id == "unitcam-000001"
    assert frame.width == 11
    assert frame.height == 9
    source.release()
    assert capture.released is True


def test_runtime_factory_builds_mock_sources_when_allowed() -> None:
    config = {
        "sensor": {"source": "mock"},
        "telemetry": {"source": "mock"},
    }
    assert build_frame_source_from_config(config, allow_mock=True).read().width > 0
    assert build_telemetry_source_from_config(config, allow_mock=True).read().lat_deg
