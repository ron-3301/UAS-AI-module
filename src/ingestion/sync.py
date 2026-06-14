from __future__ import annotations

# frame <-> telemetry synchroniser (layer 1).
# simplified version of the algo in docs/13 §4 - good enough for bench
# rig + replay paths:
#   frame's wall-clock UTC is matched to nearest sample in the buffer.
#   if skew > max_stale_ms, packet is flagged telemetry_stale.
# downstream then decides whether to suppress (docs/12 §5) or interpolate
# (geolocation layer).


from datetime import datetime, timezone

from src.ingestion.frame_capture import CapturedFrame
from src.ingestion.telemetry_parser import TelemetryParser, TelemetrySample
from src.types import FramePacket


def _parse_utc_iso(s: str) -> float:
    # accepts '2026-06-08T12:00:00.123Z' and similar
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    has_tz = "+" in s or "-" in s[-6:]
    if has_tz:
        return datetime.fromisoformat(s).timestamp()
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


class Synchroniser:
    def __init__(self, telemetry: TelemetryParser, max_stale_ms: int = 1000) -> None:
        self.telemetry = telemetry
        self.max_stale_ms = max_stale_ms

    def make_packet(self, frame: CapturedFrame) -> FramePacket:
        ts = _parse_utc_iso(frame.timestamp_utc)
        sample: TelemetrySample | None = self.telemetry.nearest(ts)

        stale = True
        if sample is not None:
            skew_ms = abs(sample.timestamp_utc - ts) * 1000.0
            stale = skew_ms > self.max_stale_ms

        return FramePacket(
            frame_id=frame.frame_id,
            timestamp_utc=frame.timestamp_utc,
            image=frame.image,
            telemetry=sample.as_dict() if sample is not None else {},
            telemetry_stale=stale or sample is None,
            capture_latency_ms=frame.capture_latency_ms,
        )
