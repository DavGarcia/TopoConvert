"""Result types for core module return values."""
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any


@dataclass
class ProcessingResult:
    """Base result type for all processing operations."""
    success: bool
    output_file: str
    message: str = ""
    details: Dict[str, Any] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.warnings is None:
            self.warnings = []


@dataclass
class PointExtractionResult(ProcessingResult):
    """Result from point extraction operations."""
    point_count: int = 0
    format: str = ""
    elevation_units: str = ""
    coordinate_system: str = ""
    coordinate_ranges: Dict[str, Tuple[float, float]] = None
    reference_point: Optional[Tuple[float, float, float]] = None
    translated_to_origin: bool = False


@dataclass
class ContourGenerationResult(ProcessingResult):
    """Result from contour generation operations."""
    contour_count: int = 0
    elevation_levels: int = 0
    contour_interval: float = 0.0
    elevation_range: Tuple[float, float] = (0.0, 0.0)
    coordinate_system: str = ""
    reference_point: Optional[Tuple[float, float, float]] = None
    translated_to_origin: bool = False


@dataclass
class MeshGenerationResult(ProcessingResult):
    """Result from mesh generation operations."""
    face_count: int = 0
    vertex_count: int = 0
    edge_count: int = 0
    mesh_type: str = ""
    has_wireframe: bool = False
    layer_name: str = ""
    coordinate_system: str = ""
    reference_point: Optional[Tuple[float, float, float]] = None
    translated_to_origin: bool = False


@dataclass
class GridGenerationResult(ProcessingResult):
    """Result from GPS grid generation operations."""
    grid_points: int = 0
    spacing: float = 0.0
    boundary_type: str = ""
    buffer: Optional[float] = None


@dataclass
class CSVToKMLResult(ProcessingResult):
    """Result from CSV to KML conversion."""
    valid_points: int = 0
    elevation_units: str = ""
    point_style: str = ""
    has_labels: bool = False
    coordinate_bounds: Dict[str, Tuple[float, float]] = None


@dataclass
class KMLContoursResult(ProcessingResult):
    """Result from KML contours to DXF conversion."""
    contour_count: int = 0
    missing_elevations: int = 0
    coordinate_system: str = ""
    xy_units: str = ""
    z_units: str = ""
    reference_point: Optional[Tuple[float, float]] = None
    translated_to_origin: bool = False


@dataclass
class CombinedKMLResult(ProcessingResult):
    """Result from combining multiple CSV files to KML."""
    input_file_count: int = 0
    total_points: int = 0
    elevations_converted: bool = False


@dataclass
class CombinedDXFResult(ProcessingResult):
    """Result from combining multiple CSV files to DXF."""
    input_file_count: int = 0
    total_points: int = 0
    layers_created: List[str] = None
    coordinate_system: str = ""
    reference_point: Optional[Tuple[float, float, float]] = None
    translated_to_origin: bool = False


@dataclass
class SlopeHeatmapResult(ProcessingResult):
    """Result from slope heatmap generation."""
    grid_resolution: Tuple[int, int] = (0, 0)
    slope_units: str = ""
    smoothing_applied: Optional[float] = None
    output_dpi: int = 0
    point_count: int = 0