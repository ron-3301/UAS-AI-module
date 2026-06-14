from __future__ import annotations

import json
from datetime import datetime, timezone

from uas_ai_module.geolocation.attitude_raycaster import AttitudeAwareGroundPlaneRaycaster
from uas_ai_module.geolocation.terrain import FlatTerrainProvider, GridTerrainProvider, load_terrain_provider
from uas_ai_module.metrics.runtime_metrics import RuntimeMetricsCollector, prometheus_text
from uas_ai_module.models import CameraIntrinsics, Detection, Frame, Telemetry
from uas_ai_module.output.jsonl_logger import AdvisoryJsonlLogger
from uas_ai_module.pipeline import Pipeline


def test_grid_terrain_provider_nearest_neighbor_and_loader(tmp_path) -> None:
    terrain_path = tmp_path / "terrain.json"
    terrain_path.write_text(json.dumps({
        "type": "grid",
        "origin_lat_deg": 28.0,
        "origin_lon_deg": 77.0,
        "resolution_deg": 0.01,
        "elevations_m": [[100.0, 110.0], [120.0, 130.0]],
    }))
    provider = load_terrain_provider(terrain_path)
    assert provider.elevation_msl_m(28.009, 77.009) == 130.0


def test_attitude_raycaster_uses_terrain_provider() -> None:
    raycaster = AttitudeAwareGroundPlaneRaycaster(
        CameraIntrinsics("cam", 640, 480, 640.0, 640.0, 320.0, 240.0),
        terrain_provider=FlatTerrainProvider(210.0),
    )
    point = raycaster.geolocate(
        Detection("Vehicle-Wheeled", 0.9, (310, 230, 330, 250)),
        Frame("f", datetime.now(timezone.utc), 640, 480, None),
        Telemetry(
            timestamp_utc=datetime.now(timezone.utc),
            lat_deg=28.0,
            lon_deg=77.0,
            alt_msl_m=300.0,
            alt_agl_m=100.0,
        ),
    )
    assert point.valid is True
    assert point.alt_msl_m == 210.0
    assert point.cep_m is not None and point.cep_m >= 3.0


def test_runtime_metrics_and_prometheus_text() -> None:
    packet = Pipeline.dry_run("metrics-test").run_once().advisory
    snapshot = RuntimeMetricsCollector().from_packet(packet)
    assert snapshot.detection_count == 1
    text = prometheus_text(snapshot)
    assert "uas_ai_detections_total 1" in text
    assert "uas_ai_health_status" in text


def test_advisory_jsonl_logger_round_trip(tmp_path) -> None:
    packet = Pipeline.dry_run("logger-test").run_once().advisory
    path = tmp_path / "logs" / "advisory.jsonl"
    logger = AdvisoryJsonlLogger(path)
    logger.write(packet)
    assert logger.read_all()[0]["uas_id"] == "logger-test"
