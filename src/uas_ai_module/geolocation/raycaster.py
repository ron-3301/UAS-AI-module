"""Basic pinhole ray-to-ground geolocation.

This implementation is intentionally conservative. It provides a deterministic,
testable geolocation path for the rebuild MVP and marks invalid/uncertain cases
explicitly instead of pretending high precision.
"""
from __future__ import annotations

import math

from uas_ai_module.models import CameraIntrinsics, Detection, Frame, GeoPoint, Telemetry

EARTH_RADIUS_M = 6_378_137.0


class GroundPlaneRaycaster:
    """Estimate ground intersection for a detection using a down-looking camera.

    The MVP assumes a mostly nadir/down-looking camera and a locally flat ground
    plane at ownship AGL. DTED/terrain support can replace this class later while
    preserving the same safe failure behavior.
    """

    def __init__(self, intrinsics: CameraIntrinsics) -> None:
        intrinsics.validate()
        self.intrinsics = intrinsics

    @classmethod
    def from_config_dict(cls, data: dict) -> "GroundPlaneRaycaster":
        resolution = data["resolution"]
        mount = data.get("mount", {})
        rotation = mount.get("rotation_deg", {})
        intrinsics = CameraIntrinsics(
            camera_id=data["camera_id"],
            width=int(resolution["width"]),
            height=int(resolution["height"]),
            fx=float(data["fx"]),
            fy=float(data["fy"]),
            cx=float(data["cx"]),
            cy=float(data["cy"]),
            mount_roll_deg=float(rotation.get("roll", 0.0)),
            mount_pitch_deg=float(rotation.get("pitch", -90.0)),
            mount_yaw_deg=float(rotation.get("yaw", 0.0)),
        )
        return cls(intrinsics)

    def geolocate(self, detection: Detection, frame: Frame, telemetry: Telemetry) -> GeoPoint:
        """Return an estimated object location.

        Failure cases return a `GeoPoint` with `valid=False` and a reason rather
        than raising through the pipeline.
        """

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

        agl = telemetry.alt_agl_m

        # Default camera convention: image right => east, image down => south
        # when yaw is zero. Rotate horizontal offset by ownship yaw plus mount
        # yaw. This is a first-order flat-ground estimate.
        north_cam_m = -y_norm * agl
        east_cam_m = x_norm * agl

        yaw_rad = math.radians(telemetry.yaw_deg + self.intrinsics.mount_yaw_deg)
        cos_yaw = math.cos(yaw_rad)
        sin_yaw = math.sin(yaw_rad)
        north_m = north_cam_m * cos_yaw - east_cam_m * sin_yaw
        east_m = north_cam_m * sin_yaw + east_cam_m * cos_yaw

        lat_rad = math.radians(telemetry.lat_deg)
        d_lat = north_m / EARTH_RADIUS_M
        cos_lat = max(math.cos(lat_rad), 1e-9)
        d_lon = east_m / (EARTH_RADIUS_M * cos_lat)

        lat = telemetry.lat_deg + math.degrees(d_lat)
        lon = telemetry.lon_deg + math.degrees(d_lon)
        alt_msl = telemetry.alt_msl_m - agl

        # Conservative first-order CEP. Real implementation should propagate
        # calibration/pose/range covariance.
        box_w = max(0.0, x2 - x1)
        box_h = max(0.0, y2 - y1)
        box_scale = math.hypot(box_w / frame.width, box_h / frame.height)
        cep_m = max(3.0, 0.03 * agl + 2.0 * box_scale)

        return GeoPoint(lat, lon, alt_msl_m=alt_msl, cep_m=cep_m, valid=True)
