from __future__ import annotations

# --- OLD CODE FROM SRC ---
from typing import Dict, Any
class TelemetryParser:
    def __init__(self): self.last = {"lat": 0.0, "lon": 0.0, "alt_agl_m": 100.0}
    def parse(self, mavlink_msg: Dict[str, Any]) -> Dict[str, Any]: return self.last

# --- END OLD CODE ---

"""Telemetry source abstractions."""


from typing import Protocol

from models import Telemetry, utc_now


class TelemetrySource(Protocol):
    """Interface implemented by telemetry sources."""

    def read(self) -> Telemetry:
        """Return the latest ownship telemetry."""


class MockTelemetrySource:
    """Deterministic telemetry source for tests and dry-runs."""

    def __init__(
        self,
        lat_deg: float = 28.6139,
        lon_deg: float = 77.2090,
        alt_msl_m: float = 300.0,
        alt_agl_m: float = 120.0,
        yaw_deg: float = 0.0,
    ) -> None:
        self.lat_deg = lat_deg
        self.lon_deg = lon_deg
        self.alt_msl_m = alt_msl_m
        self.alt_agl_m = alt_agl_m
        self.yaw_deg = yaw_deg

    def read(self) -> Telemetry:
        return Telemetry(
            timestamp_utc=utc_now(),
            lat_deg=self.lat_deg,
            lon_deg=self.lon_deg,
            alt_msl_m=self.alt_msl_m,
            alt_agl_m=self.alt_agl_m,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=self.yaw_deg,
            velocity_ned_mps=(0.0, 0.0, 0.0),
        )
