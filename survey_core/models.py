"""Data models and immutable state container for `survey_core`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class LocalOrigin:
    """Reference origin used to shift large UTM coordinates to local meters."""

    e0: float = 0.0
    n0: float = 0.0
    z0: float = 0.0

    def to_local(
        self, easting: float, northing: float, elevation: float
    ) -> tuple[float, float, float]:
        """Convert global UTM (E, N, Z) to local (x, y, z) meters."""
        return (easting - self.e0, northing - self.n0, elevation - self.z0)

    def to_global(
        self, x_local: float, y_local: float, z_local: float
    ) -> tuple[float, float, float]:
        """Convert local (x, y, z) meters back to global UTM (E, N, Z)."""
        return (x_local + self.e0, y_local + self.n0, z_local + self.z0)

    def to_local_xy(self, easting: float, northing: float) -> tuple[float, float]:
        """Convert global (E, N) to local (x, y)."""
        return (easting - self.e0, northing - self.n0)

    def to_global_xy(self, x_local: float, y_local: float) -> tuple[float, float]:
        """Convert local (x, y) back to global (E, N)."""
        return (x_local + self.e0, y_local + self.n0)

    def to_dict(self) -> dict[str, float]:
        """Serialize local origin to dictionary."""
        return {"e0": float(self.e0), "n0": float(self.n0), "z0": float(self.z0)}


@dataclass(frozen=True)
class SurveyPoint:
    """Single survey observation in both global UTM and shifted local coordinates."""

    id: str
    index: int
    code: str
    easting: float
    northing: float
    elevation: float
    x_local: float
    y_local: float
    z_local: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize point for JSON payloads."""
        return {
            "id": self.id,
            "index": self.index,
            "code": self.code,
            "easting": round(self.easting, 4),
            "northing": round(self.northing, 4),
            "elevation": round(self.elevation, 4),
            "x": round(self.x_local, 4),
            "y": round(self.y_local, 4),
            "z": round(self.z_local, 4),
        }


@dataclass(frozen=True)
class RemovedPoint:
    """Survey point removed during cleaning with reason and diagnostic value."""

    point: SurveyPoint
    reason: str  # "duplicate" or "outlier"
    metric_value: float
    detail: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize removed point for stats and viewer highlighting."""
        d = self.point.to_dict()
        d["reason"] = self.reason
        d["metric_value"] = round(self.metric_value, 4)
        d["detail"] = self.detail
        return d


@dataclass(frozen=True)
class CodeConfig:
    """Configuration and role assignment for a survey point code."""

    code: str
    count: int
    role: str = "point"  # "point" | "breakline" | "boundary" | "ignore"
    color: str = "#38bdf8"

    def to_dict(self) -> dict[str, Any]:
        """Serialize code configuration."""
        return {
            "code": self.code,
            "count": self.count,
            "role": self.role,
            "color": self.color,
        }


@dataclass(frozen=True)
class ContourLine:
    """Single contour polyline extracted on the filtered TIN."""

    elevation: float
    z_local: float
    is_major: bool
    points_local: list[tuple[float, float]]
    label_pos_local: tuple[float, float, float] | None = None  # (x, y, angle_deg)

    def to_dict(self, origin: LocalOrigin) -> dict[str, Any]:
        """Serialize contour line for viewer payload."""
        return {
            "elevation": round(self.elevation, 3),
            "z": round(self.z_local, 3),
            "is_major": self.is_major,
            "points": [[round(px, 3), round(py, 3)] for px, py in self.points_local],
            "label": (
                {
                    "x": round(self.label_pos_local[0], 3),
                    "y": round(self.label_pos_local[1], 3),
                    "angle": round(self.label_pos_local[2], 1),
                    "text": (
                        f"{self.elevation:.2f}"
                        if abs(self.elevation - round(self.elevation)) > 1e-3
                        else f"{self.elevation:.1f}"
                    ),
                }
                if self.label_pos_local is not None
                else None
            ),
        }


@dataclass(frozen=True)
class SurveyState:
    """Complete state of a topographic survey pipeline session."""

    raw_text: str = ""
    filename: str = "survey.txt"
    crs: str = "EPSG:32640"
    crs_name: str = "WGS 84 / UTM zone 40N"
    crs_is_assumed: bool = True
    detected_delimiter: str = ","
    delimiter_name: str = "comma"
    has_header: bool = False
    ne_swapped_heuristic: bool = False
    ne_swap_applied: bool = False
    ne_order_uncertain: bool = False
    ne_heuristic_reason: str = ""
    origin: LocalOrigin = field(default_factory=LocalOrigin)
    raw_points: list[SurveyPoint] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)

    # Step 2: Clean
    cleaned_points: list[SurveyPoint] = field(default_factory=list)
    removed_points: list[RemovedPoint] = field(default_factory=list)
    clean_params: dict[str, Any] = field(default_factory=dict)

    # Step 3: Codes
    code_configs: dict[str, CodeConfig] = field(default_factory=dict)
    active_points: list[SurveyPoint] = field(default_factory=list)
    breaklines_local: list[dict[str, Any]] = field(default_factory=list)
    boundary_codes_polygon_local: list[tuple[float, float]] | None = None
    holes_local: list[list[tuple[float, float]]] = field(default_factory=list)

    # Step 4: TIN
    tin_vertices_local: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 3), dtype=np.float64)
    )
    tin_point_ids: list[str] = field(default_factory=list)
    tin_point_codes: list[str] = field(default_factory=list)
    tin_triangles: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 3), dtype=np.int32)
    )
    tin_method: str = "scipy_delaunay"
    tin_method_note: str = ""
    breakline_edges: list[tuple[int, int]] = field(default_factory=list)

    # Step 5: Filter
    filtered_triangles: np.ndarray = field(
        default_factory=lambda: np.zeros((0, 3), dtype=np.int32)
    )
    triangle_mask: np.ndarray = field(
        default_factory=lambda: np.zeros((0,), dtype=bool)
    )
    filter_params: dict[str, Any] = field(default_factory=dict)
    boundary_polygon_local: list[tuple[float, float]] | None = None

    # Step 6: Contours
    contours: list[ContourLine] = field(default_factory=list)
    contour_params: dict[str, Any] = field(default_factory=dict)
    triangle_slopes_deg: np.ndarray = field(
        default_factory=lambda: np.zeros((0,), dtype=np.float64)
    )
    triangle_slopes_pct: np.ndarray = field(
        default_factory=lambda: np.zeros((0,), dtype=np.float64)
    )
    slope_grid_data: dict[str, Any] | None = None

    # Step 7: Metrics & Report
    metrics: dict[str, Any] = field(default_factory=dict)
    profile_data: dict[str, Any] = field(default_factory=dict)

    # Pipeline tracking
    completed_steps: list[int] = field(default_factory=list)
    step_stats: dict[int, dict[str, Any]] = field(default_factory=dict)
