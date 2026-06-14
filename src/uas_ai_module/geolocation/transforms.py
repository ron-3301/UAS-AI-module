"""Small attitude/rotation helpers for geolocation hardening."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def rotation_matrix_zyx(roll_deg: float, pitch_deg: float, yaw_deg: float) -> np.ndarray:
    """Return body-to-world rotation for ZYX yaw/pitch/roll Euler angles."""

    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(yaw_deg)

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    return rz @ ry @ rx


def pinhole_camera_ray(x_norm: float, y_norm: float) -> np.ndarray:
    """Return a normalized camera ray from pinhole normalized image coords."""

    ray = np.array([float(x_norm), float(y_norm), 1.0], dtype=np.float64)
    norm = np.linalg.norm(ray)
    if norm <= 0:
        raise ValueError("camera ray norm is zero")
    return ray / norm


def apply_rotation(rotation: np.ndarray, vector: Iterable[float]) -> np.ndarray:
    """Apply a 3x3 rotation matrix to a vector."""

    rot = np.asarray(rotation, dtype=np.float64)
    vec = np.asarray(tuple(vector), dtype=np.float64)
    if rot.shape != (3, 3):
        raise ValueError("rotation must be 3x3")
    if vec.shape != (3,):
        raise ValueError("vector must have shape (3,)")
    return rot @ vec
