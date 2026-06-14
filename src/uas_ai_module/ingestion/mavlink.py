"""Read-only MAVLink telemetry ingestion.

This module deliberately implements telemetry receive only. It does not send
commands, mission items, mode changes, or actuator messages.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from uas_ai_module.models import Telemetry


class MavlinkTelemetryError(RuntimeError):
    """Raised when telemetry cannot be obtained or parsed safely."""


class MavlinkTelemetrySource:
    """Read ownship telemetry from a MAVLink connection.

    Args:
        endpoint: pymavlink connection string, e.g. `udp:0.0.0.0:14550`.
        connection: optional injected connection for tests. It must expose
            `recv_match(type=..., blocking=..., timeout=...)`.
        timeout_s: receive timeout per `read()` call.

    Safety posture:
        This class is read-only and never calls MAVLink send APIs.
    """

    READ_TYPES = ("GLOBAL_POSITION_INT", "ATTITUDE", "VFR_HUD")

    def __init__(
        self,
        endpoint: str = "udp:0.0.0.0:14550",
        *,
        connection: Any | None = None,
        timeout_s: float = 1.0,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self._connection = connection
        self._position: dict[str, float] | None = None
        self._attitude: dict[str, float] = {"roll_deg": 0.0, "pitch_deg": 0.0, "yaw_deg": 0.0}

    @property
    def connection(self) -> Any:
        if self._connection is None:
            try:
                from pymavlink import mavutil  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise MavlinkTelemetryError("pymavlink is required for MAVLink telemetry") from exc
            self._connection = mavutil.mavlink_connection(self.endpoint)
        return self._connection

    def read(self) -> Telemetry:
        """Read until a valid global position is available or timeout occurs."""

        deadline_messages = max(1, len(self.READ_TYPES) * 4)
        for _ in range(deadline_messages):
            msg = self.connection.recv_match(type=list(self.READ_TYPES), blocking=True, timeout=self.timeout_s)
            if msg is None:
                break
            self._handle_message(msg)
            if self._position is not None:
                return self._build_telemetry()
        raise MavlinkTelemetryError("timed out waiting for GLOBAL_POSITION_INT telemetry")

    def _handle_message(self, msg: Any) -> None:
        msg_type = _message_type(msg)
        if msg_type == "GLOBAL_POSITION_INT":
            self._position = _parse_global_position_int(msg)
        elif msg_type == "ATTITUDE":
            self._attitude.update(_parse_attitude(msg))
        elif msg_type == "VFR_HUD":
            # Used only as a fallback heading if ATTITUDE has not been seen.
            heading = getattr(msg, "heading", None)
            if heading is not None and self._attitude.get("yaw_deg", 0.0) == 0.0:
                self._attitude["yaw_deg"] = float(heading) % 360.0

    def _build_telemetry(self) -> Telemetry:
        assert self._position is not None
        pos = self._position
        return Telemetry(
            timestamp_utc=datetime.now(timezone.utc),
            lat_deg=pos["lat_deg"],
            lon_deg=pos["lon_deg"],
            alt_msl_m=pos["alt_msl_m"],
            alt_agl_m=pos.get("alt_agl_m"),
            roll_deg=self._attitude.get("roll_deg", 0.0),
            pitch_deg=self._attitude.get("pitch_deg", 0.0),
            yaw_deg=self._attitude.get("yaw_deg", 0.0),
            velocity_ned_mps=(pos.get("vn_mps", 0.0), pos.get("ve_mps", 0.0), pos.get("vd_mps", 0.0)),
        )


def _message_type(msg: Any) -> str:
    if hasattr(msg, "get_type"):
        return str(msg.get_type())
    return str(getattr(msg, "type", ""))


def _parse_global_position_int(msg: Any) -> dict[str, float]:
    lat_raw = getattr(msg, "lat", None)
    lon_raw = getattr(msg, "lon", None)
    alt_raw = getattr(msg, "alt", None)
    if lat_raw is None or lon_raw is None or alt_raw is None:
        raise MavlinkTelemetryError("GLOBAL_POSITION_INT missing lat/lon/alt")

    lat_deg = float(lat_raw) / 1e7
    lon_deg = float(lon_raw) / 1e7
    alt_msl_m = float(alt_raw) / 1000.0
    rel_alt = getattr(msg, "relative_alt", None)
    alt_agl_m = float(rel_alt) / 1000.0 if rel_alt is not None else None

    if not -90 <= lat_deg <= 90 or not -180 <= lon_deg <= 180:
        raise MavlinkTelemetryError("GLOBAL_POSITION_INT lat/lon out of range")

    return {
        "lat_deg": lat_deg,
        "lon_deg": lon_deg,
        "alt_msl_m": alt_msl_m,
        "alt_agl_m": alt_agl_m,
        "vn_mps": float(getattr(msg, "vx", 0.0)) / 100.0,
        "ve_mps": float(getattr(msg, "vy", 0.0)) / 100.0,
        "vd_mps": float(getattr(msg, "vz", 0.0)) / 100.0,
    }


def _parse_attitude(msg: Any) -> dict[str, float]:
    roll = float(getattr(msg, "roll", 0.0))
    pitch = float(getattr(msg, "pitch", 0.0))
    yaw = float(getattr(msg, "yaw", 0.0))
    return {
        "roll_deg": math.degrees(roll),
        "pitch_deg": math.degrees(pitch),
        "yaw_deg": math.degrees(yaw) % 360.0,
    }
