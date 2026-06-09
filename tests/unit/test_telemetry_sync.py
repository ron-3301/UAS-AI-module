# tests for telemetry buffer + frame sync.
from __future__ import annotations

from datetime import datetime, timezone

from src.ingestion.frame_capture import CapturedFrame
from src.ingestion.sync import Synchroniser
from src.ingestion.telemetry_parser import TelemetryParser, TelemetrySample


def _ts_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def _sample(ts: float, **overrides) -> TelemetrySample:
    defaults = dict(
        timestamp_utc=ts, lat=10.0, lon=20.0,
        alt_msl_m=200.0, alt_agl_m=100.0,
        roll_deg=0.0, pitch_deg=-10.0, yaw_deg=45.0,
    )
    defaults.update(overrides)
    return TelemetrySample(**defaults)


def test_telemetry_buffer_latest_and_nearest() -> None:
    tp = TelemetryParser(udp_port=14550)
    base = datetime.now(timezone.utc).timestamp()
    tp.feed([_sample(base + i * 0.1, lat=10.0 + i) for i in range(5)])
    assert tp.latest().lat == 14.0
    nearest = tp.nearest(base + 0.25)
    assert nearest.lat in (12.0, 13.0)  # closest is at 0.2 or 0.3


def test_sync_marks_fresh_packet() -> None:
    tp = TelemetryParser(udp_port=14550)
    base_dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
    base_ts = base_dt.timestamp()
    tp.feed([_sample(base_ts)])
    sync = Synchroniser(tp, max_stale_ms=500)
    import numpy as np
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    frame = CapturedFrame(frame_id=1, timestamp_utc=_ts_iso(base_dt),
                          image=img, capture_latency_ms=0.0)
    pkt = sync.make_packet(frame)
    assert pkt.telemetry_stale is False
    assert pkt.telemetry["lat"] == 10.0


def test_sync_marks_stale_when_offset_too_big() -> None:
    tp = TelemetryParser(udp_port=14550)
    base_dt = datetime(2026, 6, 8, 12, 0, 0, tzinfo=timezone.utc)
    # Telemetry sample 3 seconds in the past.
    tp.feed([_sample(base_dt.timestamp() - 3.0)])
    sync = Synchroniser(tp, max_stale_ms=500)
    import numpy as np
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    frame = CapturedFrame(frame_id=1, timestamp_utc=_ts_iso(base_dt),
                          image=img, capture_latency_ms=0.0)
    pkt = sync.make_packet(frame)
    assert pkt.telemetry_stale is True


def test_sync_marks_stale_when_buffer_empty() -> None:
    tp = TelemetryParser(udp_port=14550)
    sync = Synchroniser(tp, max_stale_ms=500)
    import numpy as np
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    frame = CapturedFrame(frame_id=1, timestamp_utc=_ts_iso(datetime.now(timezone.utc)),
                          image=img, capture_latency_ms=0.0)
    pkt = sync.make_packet(frame)
    assert pkt.telemetry_stale is True
    assert pkt.telemetry == {}
