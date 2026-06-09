# MAVLink telemetry parser with a 1-second ring buffer.
# pymavlink is NOT imported at module load - connection setup is heavy,
# and tests + file-based replay don't need it.
#
# api:
#   TelemetryParser(udp_port).start()
#   .latest()        -> latest sample or None
#   .nearest(utc_ts) -> closest sample to utc_ts or None
#   .stop()
from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass
class TelemetrySample:
    # one sample as seen by the rest of the pipeline
    timestamp_utc: float            # seconds since epoch
    lat: float
    lon: float
    alt_msl_m: float
    alt_agl_m: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    groundspeed_mps: float = 0.0
    heading_deg: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "lat": self.lat, "lon": self.lon,
            "alt_msl_m": self.alt_msl_m, "alt_agl_m": self.alt_agl_m,
            "roll": self.roll_deg, "pitch": self.pitch_deg, "yaw": self.yaw_deg,
            "groundspeed": self.groundspeed_mps, "heading": self.heading_deg,
            "timestamp_utc": self.timestamp_utc,
        }


class TelemetryParser:
    # background-thread MAVLink reader with a ring buffer of samples.
    def __init__(self, udp_port: int = 14550, buffer_seconds: float = 1.0,
                 max_samples: int = 200) -> None:
        self.udp_port = udp_port
        self.buffer_seconds = buffer_seconds
        self._buf: deque[TelemetrySample] = deque(maxlen=max_samples)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- lifecycle ----
    def start(self) -> None:  # pragma: no cover - real MAVLink only
        from pymavlink import mavutil  # type: ignore
        conn = mavutil.mavlink_connection(f"udp:0.0.0.0:{self.udp_port}")
        self._thread = threading.Thread(target=self._read_loop, args=(conn,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    # ---- accessors ----
    def latest(self) -> TelemetrySample | None:
        with self._lock:
            return self._buf[-1] if self._buf else None

    def nearest(self, utc_ts: float) -> TelemetrySample | None:
        with self._lock:
            if not self._buf:
                return None
            return min(self._buf, key=lambda s: abs(s.timestamp_utc - utc_ts))

    # ---- inject (tests + replay) ----
    def feed(self, samples: Iterable[TelemetrySample]) -> None:
        # bulk-load samples (used by replay & tests).
        with self._lock:
            for s in samples:
                self._buf.append(s)

    def push(self, sample: TelemetrySample) -> None:
        with self._lock:
            self._buf.append(sample)

    # ---- internal ----
    def _read_loop(self, conn: Any) -> None:  # pragma: no cover - real MAVLink only
        st = {
            "lat": 0.0, "lon": 0.0, "alt_msl_m": 0.0, "alt_agl_m": 0.0,
            "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
            "groundspeed": 0.0, "heading": 0.0,
        }
        while not self._stop.is_set():
            msg = conn.recv_match(blocking=True, timeout=0.5)
            if msg is None:
                continue
            kind = msg.get_type()
            if kind == "GLOBAL_POSITION_INT":
                st["lat"] = msg.lat * 1e-7
                st["lon"] = msg.lon * 1e-7
                st["alt_msl_m"] = msg.alt / 1000.0
                st["alt_agl_m"] = msg.relative_alt / 1000.0
            elif kind == "ATTITUDE":
                import math
                st["roll"]  = math.degrees(msg.roll)
                st["pitch"] = math.degrees(msg.pitch)
                st["yaw"]   = math.degrees(msg.yaw)
            elif kind == "VFR_HUD":
                st["groundspeed"] = msg.groundspeed
                st["heading"]     = msg.heading
            else:
                continue
            self.push(TelemetrySample(
                timestamp_utc=time.time(),
                lat=st["lat"], lon=st["lon"],
                alt_msl_m=st["alt_msl_m"], alt_agl_m=st["alt_agl_m"],
                roll_deg=st["roll"], pitch_deg=st["pitch"], yaw_deg=st["yaw"],
                groundspeed_mps=st["groundspeed"], heading_deg=st["heading"],
            ))
