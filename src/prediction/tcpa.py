from __future__ import annotations

# --- OLD CODE FROM SRC ---
import math
from typing import Dict

def compute_tcpa(ownship, target, horizon=30.0):
    rel_lat = target["lat"] - ownship["lat"]
    rel_lon = target["lon"] - ownship["lon"]
    rel_speed = math.sqrt(rel_lat**2 + rel_lon**2)
    if rel_speed < 1e-6:
        return {"tcpa_s": 999.0, "closest_distance_m": 0.0}
    tcpa = min(horizon, rel_speed / 0.0001)
    closest = rel_speed * 111000
    return {"tcpa_s": round(tcpa, 1), "closest_distance_m": round(closest, 1)}
# --- END OLD CODE ---

"""Time to closest point of approach (TCPA) helper."""


from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TcpaResult:
    tcpa_s: float
    closest_approach_m: float
    is_converging: bool


def compute_tcpa(
    relative_position_m: tuple[float, float],
    relative_velocity_mps: tuple[float, float],
    *,
    max_horizon_s: float = 300.0,
    min_relative_speed_mps: float = 0.1,
) -> TcpaResult:
    """Compute 2D TCPA using relative position and velocity.

    Args:
        relative_position_m: target position relative to ownship as (north, east).
        relative_velocity_mps: target velocity relative to ownship as
            (north_rate, east_rate).
        max_horizon_s: returned TCPA is clamped to this horizon.
        min_relative_speed_mps: below this speed the objects are considered
            effectively stationary relative to each other.
    """

    px, py = relative_position_m
    vx, vy = relative_velocity_mps
    speed_sq = vx * vx + vy * vy
    current_range = math.hypot(px, py)

    if speed_sq < min_relative_speed_mps * min_relative_speed_mps:
        return TcpaResult(tcpa_s=0.0, closest_approach_m=current_range, is_converging=False)

    unconstrained_t = -((px * vx) + (py * vy)) / speed_sq
    is_converging = unconstrained_t > 0.0
    tcpa_s = min(max(unconstrained_t, 0.0), max_horizon_s)
    closest_x = px + vx * tcpa_s
    closest_y = py + vy * tcpa_s
    return TcpaResult(
        tcpa_s=tcpa_s,
        closest_approach_m=math.hypot(closest_x, closest_y),
        is_converging=is_converging,
    )
