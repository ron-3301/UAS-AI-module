"""Attitude-aware pinhole ground-plane raycaster.

This is still a local flat-ground estimator, but it uses camera normalized ray
geometry plus ownship attitude to prepare for the later terrain/covariance model.
Coordinates use a local NED convention: north, east, down.
"""
from __future__ import annotations

import math

import numpy as np

from uas_ai_module.geolocation.raycaster import EARTH_RADIUS_M
from uas_ai_module.geolocation.transforms import rotation_matrix_zyx
from uas_ai_module.geolocation.terrain import TerrainProvider
from uas_ai_module.models import CameraIntrinsics, Detection, Frame, GeoPoint, Telemetry


class AttitudeAwareGroundPlaneRaycaster:
    """Estimate ground intersection using ownship roll/pitch/yaw.

    For a zero-attitude nadir camera, center pixels intersect directly below the
    ownship. Image right maps to east; image down maps to south.
    """

    def __init__(self, intrinsics: CameraIntrinsics, terrain_provider: TerrainProvider | None = None) -> None:
        intrinsics.validate()
        self.intrinsics = intrinsics
        self.terrain_provider = terrain_provider

    def geolocate(self, detection: Detection, frame: Frame, telemetry: Telemetry) -> GeoPoint:
        try:
            detection.validate()
        except ValueError as exc:
            return GeoPoint(None, None, cep_m=None, valid=False, reason=f"invalid_detection: {exc}")
        if telemetry.alt_agl_m is None or telemetry.alt_agl_m <= 0:
            return GeoPoint(None, None, cep_m=None, valid=False, reason="missing_or_invalid_agl")
        if frame.width <= 0 or frame.height <= 0:
            return GeoPoint(None, None, cep_m=None, valid=False, reason="invalid_frame_size")

        x1, y1, x2, y2 = detection.bbox_xyxy
        u = (x1 + x2) / 2.0
        v = (y1 + y2) / 2.0
        if not (0.0 <= u <= frame.width and 0.0 <= v <= frame.height):
            return GeoPoint(None, None, cep_m=None, valid=False, reason="bbox_center_outside_frame")

        x_norm = (u - self.intrinsics.cx) / self.intrinsics.fx
        y_norm = (v - self.intrinsics.cy) / self.intrinsics.fy

        # Camera ray mapped to body/NED-like axes for nadir mount:
        # x image right -> east, y image down -> south, optical axis -> down.
        ray_body = np.asarray((-y_norm, x_norm, 1.0), dtype=np.float64)
        ray_body /= np.linalg.norm(ray_body)

        rotation = rotation_matrix_zyx(
            telemetry.roll_deg + self.intrinsics.mount_roll_deg,
            telemetry.pitch_deg,
            telemetry.yaw_deg + self.intrinsics.mount_yaw_deg,
        )
        ray_ned = rotation @ ray_body
        down = float(ray_ned[2])
        if down <= 1e-6:
            return GeoPoint(None, None, cep_m=None, valid=False, reason="ray_does_not_intersect_ground")

        ground_msl = telemetry.alt_msl_m - telemetry.alt_agl_m
        lat = telemetry.lat_deg
        lon = telemetry.lon_deg
        north_m = 0.0
        east_m = 0.0

        # If a terrain provider is available, iteratively intersect the ray with
        # terrain elevation at the projected point. This remains a local
        # flat-earth approximation, but it is a safe hook for DTED providers.
        for _ in range(4):
            if self.terrain_provider is not None:
                ground_msl = self.terrain_provider.elevation_msl_m(lat, lon)
            vertical_distance_m = telemetry.alt_msl_m - ground_msl
            if vertical_distance_m <= 0:
                return GeoPoint(None, None, cep_m=None, valid=False, reason="ownship_below_terrain")
            scale = vertical_distance_m / down
            north_m = float(ray_ned[0] * scale)
            east_m = float(ray_ned[1] * scale)
            lat_rad = math.radians(telemetry.lat_deg)
            lat = telemetry.lat_deg + math.degrees(north_m / EARTH_RADIUS_M)
            lon = telemetry.lon_deg + math.degrees(east_m / (EARTH_RADIUS_M * max(math.cos(lat_rad), 1e-9)))

        attitude_penalty = 0.02 * max(0.0, telemetry.alt_msl_m - ground_msl) * (
            abs(math.sin(math.radians(telemetry.roll_deg))) + abs(math.sin(math.radians(telemetry.pitch_deg)))
        )
        terrain_penalty = 2.0 if self.terrain_provider is not None else 0.0
        cep_m = max(3.0, 0.03 * max(0.0, telemetry.alt_msl_m - ground_msl) + attitude_penalty + terrain_penalty)
        return GeoPoint(lat, lon, alt_msl_m=ground_msl, cep_m=cep_m, valid=True)
