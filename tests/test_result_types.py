"""Tests for result types."""
import pytest
from topoconvert.core.result_types import (
    ProcessingResult, PointExtractionResult, ContourGenerationResult,
    MeshGenerationResult, GridGenerationResult, CSVToKMLResult,
    KMLContoursResult, CombinedKMLResult, CombinedDXFResult,
    SlopeHeatmapResult
)


def test_processing_result_defaults():
    """Test ProcessingResult default values."""
    result = ProcessingResult(success=True, output_file="test.txt")
    assert result.success is True
    assert result.output_file == "test.txt"
    assert result.message == ""
    assert result.details == {}
    assert result.warnings == []


def test_processing_result_with_values():
    """Test ProcessingResult with all values."""
    result = ProcessingResult(
        success=False,
        output_file="test.txt",
        message="Error occurred",
        details={"error": "details"},
        warnings=["warning1", "warning2"]
    )
    assert result.success is False
    assert result.message == "Error occurred"
    assert result.details == {"error": "details"}
    assert result.warnings == ["warning1", "warning2"]


def test_point_extraction_result():
    """Test PointExtractionResult."""
    result = PointExtractionResult(
        success=True,
        output_file="points.csv",
        point_count=100,
        format="csv",
        elevation_units="meters",
        coordinate_system="WGS84",
        coordinate_ranges={
            "x": (-122.5, -122.0),
            "y": (37.0, 37.5),
            "z": (0.0, 100.0)
        }
    )
    assert result.point_count == 100
    assert result.format == "csv"
    assert result.elevation_units == "meters"
    assert result.coordinate_system == "WGS84"
    assert result.coordinate_ranges["x"] == (-122.5, -122.0)


def test_contour_generation_result():
    """Test ContourGenerationResult."""
    result = ContourGenerationResult(
        success=True,
        output_file="contours.dxf",
        contour_count=50,
        elevation_levels=10,
        contour_interval=5.0,
        elevation_range=(0.0, 50.0),
        coordinate_system="UTM Zone 10N"
    )
    assert result.contour_count == 50
    assert result.elevation_levels == 10
    assert result.contour_interval == 5.0
    assert result.elevation_range == (0.0, 50.0)


def test_mesh_generation_result():
    """Test MeshGenerationResult."""
    result = MeshGenerationResult(
        success=True,
        output_file="mesh.dxf",
        face_count=200,
        vertex_count=150,
        edge_count=350,
        mesh_type="delaunay",
        has_wireframe=True,
        layer_name="MESH"
    )
    assert result.face_count == 200
    assert result.vertex_count == 150
    assert result.edge_count == 350
    assert result.mesh_type == "delaunay"
    assert result.has_wireframe is True


def test_grid_generation_result():
    """Test GridGenerationResult."""
    result = GridGenerationResult(
        success=True,
        output_file="grid.kml",
        grid_points=100,
        spacing=50.0,
        boundary_type="csv-extent",
        buffer=10.0
    )
    assert result.grid_points == 100
    assert result.spacing == 50.0
    assert result.boundary_type == "csv-extent"
    assert result.buffer == 10.0


def test_csv_to_kml_result():
    """Test CSVToKMLResult."""
    result = CSVToKMLResult(
        success=True,
        output_file="output.kml",
        valid_points=95,
        elevation_units="feet",
        point_style="circle",
        has_labels=True,
        coordinate_bounds={
            "lat": (37.0, 37.5),
            "lon": (-122.5, -122.0),
            "elev": (0.0, 100.0)
        }
    )
    assert result.valid_points == 95
    assert result.elevation_units == "feet"
    assert result.has_labels is True


def test_slope_heatmap_result():
    """Test SlopeHeatmapResult."""
    result = SlopeHeatmapResult(
        success=True,
        output_file="slope.png",
        grid_resolution=(100, 100),
        slope_units="degrees",
        smoothing_applied=2.0,
        output_dpi=300,
        point_count=1000
    )
    assert result.grid_resolution == (100, 100)
    assert result.slope_units == "degrees"
    assert result.smoothing_applied == 2.0
    assert result.output_dpi == 300
    assert result.point_count == 1000