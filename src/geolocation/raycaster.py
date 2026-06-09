# layer 4 stub. pinhole ray-cast to a terrain plane (flat earth or DTED).
# lands Phase 4 W11.
from __future__ import annotations


class RayCaster:
    def __init__(self, intrinsics: dict, terrain_model: str = "flat_earth") -> None:
        self.intrinsics = intrinsics
        self.terrain_model = terrain_model

    def cast(self, pixel_xy, telemetry):  # pragma: no cover - stub
        raise NotImplementedError("Ray-caster lands Phase 4 W11")
