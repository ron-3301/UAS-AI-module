"""Terrain provider interfaces for geolocation hardening.

The providers here are intentionally lightweight and deterministic. They give the
runtime a terrain abstraction without binding the rebuilt baseline to a DTED
library. A DTED-backed provider can later implement the same protocol.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TerrainProvider(Protocol):
    """Return terrain elevation above mean sea level in metres."""

    def elevation_msl_m(self, lat_deg: float, lon_deg: float) -> float:
        """Return terrain elevation MSL at a latitude/longitude."""


@dataclass(frozen=True)
class FlatTerrainProvider:
    """Constant-elevation terrain provider."""

    elevation_msl: float = 0.0

    def elevation_msl_m(self, lat_deg: float, lon_deg: float) -> float:
        _ = (lat_deg, lon_deg)
        return float(self.elevation_msl)


@dataclass(frozen=True)
class GridTerrainProvider:
    """Nearest-neighbour terrain grid provider.

    The grid JSON format is intentionally simple:

    ```json
    {
      "origin_lat_deg": 28.0,
      "origin_lon_deg": 77.0,
      "resolution_deg": 0.001,
      "elevations_m": [[210.0, 211.0], [212.0, 213.0]]
    }
    ```
    """

    origin_lat_deg: float
    origin_lon_deg: float
    resolution_deg: float
    elevations_m: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if self.resolution_deg <= 0:
            raise ValueError("terrain grid resolution must be positive")
        if not self.elevations_m or not self.elevations_m[0]:
            raise ValueError("terrain grid must not be empty")
        width = len(self.elevations_m[0])
        if any(len(row) != width for row in self.elevations_m):
            raise ValueError("terrain grid rows must have equal length")

    def elevation_msl_m(self, lat_deg: float, lon_deg: float) -> float:
        row = round((lat_deg - self.origin_lat_deg) / self.resolution_deg)
        col = round((lon_deg - self.origin_lon_deg) / self.resolution_deg)
        row_i = min(max(int(row), 0), len(self.elevations_m) - 1)
        col_i = min(max(int(col), 0), len(self.elevations_m[0]) - 1)
        return float(self.elevations_m[row_i][col_i])


class TerrainLoadError(ValueError):
    """Raised when a terrain provider cannot be loaded."""


def load_terrain_provider(path: str | Path) -> TerrainProvider:
    """Load a terrain provider from JSON.

    Supported provider types:
    - `flat`
    - `grid`
    """

    terrain_path = Path(path)
    data = json.loads(terrain_path.read_text())
    provider_type = str(data.get("type", "grid"))
    if provider_type == "flat":
        return FlatTerrainProvider(float(data.get("elevation_msl_m", 0.0)))
    if provider_type == "grid":
        try:
            rows = tuple(tuple(float(value) for value in row) for row in data["elevations_m"])
            return GridTerrainProvider(
                origin_lat_deg=float(data["origin_lat_deg"]),
                origin_lon_deg=float(data["origin_lon_deg"]),
                resolution_deg=float(data["resolution_deg"]),
                elevations_m=rows,
            )
        except KeyError as exc:
            raise TerrainLoadError(f"terrain grid missing key: {exc}") from exc
    raise TerrainLoadError(f"unsupported terrain provider type: {provider_type}")
