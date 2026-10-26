"""Comprehensive unit, golden, DXF round-trip, and synthetic fixture tests for `survey_core`."""

from __future__ import annotations

import json
import time
from pathlib import Path

import ezdxf
import pytest

from survey_core import (
    export,
    io,
    pipeline,
    report,
)
from tests.fixtures.synthetic_survey_fixtures import (
    ensure_200k_fixture,
    ensure_static_fixtures,
)

ROOT_DIR = Path(__file__).parent.parent
DEMO_PATH = ROOT_DIR / "samples" / "demo.txt"
GOLDEN_PATH = ROOT_DIR / "tests" / "golden" / "demo.json"


@pytest.fixture(scope="module")
def static_fixtures() -> dict[str, Path]:
    """Ensure all static synthetic fixtures exist on disk."""
    return ensure_static_fixtures()


class TestGoldenDemoPipeline:
    """Golden tests and DXF round-trip verification on `samples/demo.txt`."""

    def test_demo_golden_values_and_speed(self) -> None:
        assert DEMO_PATH.exists(), "samples/demo.txt must exist"
        assert GOLDEN_PATH.exists(), "tests/golden/demo.json must exist"

        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        raw_text = DEMO_PATH.read_text(encoding="utf-8")

        t0 = time.perf_counter()
        state, final_stats, viewer_payload = pipeline.run_pipeline_to_step(
            raw_text=raw_text,
            filename="demo.txt",
            up_to_step=7,
            step_params={5: {"max_edge_length": 10.0}},
        )
        elapsed = time.perf_counter() - t0
        # Exit criterion: all steps under 3 s on the demo
        assert elapsed < 3.0, f"Demo pipeline took {elapsed:.2f}s (> 3.0s limit)"

        s1 = state.step_stats[1]
        assert s1["point_count"] == golden["point_count"] == 216
        assert s1["codes"] == golden["codes"]
        assert s1["crs"]["code"] == golden["default_crs"]
        assert s1["crs"]["is_assumed"] is True

        ext = s1["extents"]
        g_ext = golden["extents"]
        assert ext["easting_min"] == pytest.approx(g_ext["easting_min"], abs=1e-3)
        assert ext["easting_max"] == pytest.approx(g_ext["easting_max"], abs=1e-3)
        assert ext["northing_min"] == pytest.approx(g_ext["northing_min"], abs=1e-3)
        assert ext["northing_max"] == pytest.approx(g_ext["northing_max"], abs=1e-3)
        assert ext["z_min"] == pytest.approx(g_ext["z_min"], abs=1e-3)
        assert ext["z_max"] == pytest.approx(g_ext["z_max"], abs=1e-3)

        # Unfiltered TIN check (~2298 m2 plan, ~2471 m2 3D)
        s4 = state.step_stats[4]
        g_unfilt = golden["unfiltered_tin"]
        assert s4["triangle_count"] == g_unfilt["triangle_count"]
        assert s4["unfiltered_plan_area_m2"] == pytest.approx(
            g_unfilt["plan_area_m2"], abs=g_unfilt["plan_area_tolerance_m2"]
        )
        assert s4["unfiltered_surface_area_3d_m2"] == pytest.approx(
            g_unfilt["surface_area_3d_m2"], abs=g_unfilt["surface_area_3d_tolerance_m2"]
        )

        # Filtered TIN (10 m max edge) check (~1028.4 m2 plan, ~1080.4 m2 3D)
        s5 = state.step_stats[5]
        g_filt = golden["filtered_tin_10m"]
        assert s5["active_triangles_after"] == g_filt["triangle_count"]
        assert s5["filtered_plan_area_m2"] == pytest.approx(
            g_filt["plan_area_m2"], abs=g_filt["plan_area_tolerance_m2"]
        )
        assert s5["filtered_surface_area_3d_m2"] == pytest.approx(
            g_filt["surface_area_3d_m2"], abs=g_filt["surface_area_3d_tolerance_m2"]
        )

        # Metrics & Report explanation
        assert final_stats["planimetric_area_m2"] == pytest.approx(
            g_filt["plan_area_m2"], abs=g_filt["plan_area_tolerance_m2"]
        )
        assert "پوسته محدب دلونی" in final_stats["strip_geometry_explanation"]
        assert viewer_payload["active_step"] == 7

    def test_demo_dxf_roundtrip_and_audit(self, tmp_path: Path) -> None:
        """Write DXF, run ezdxf audit (0 errors), read back with ezdxf, and compare every XYZ."""
        raw_text = DEMO_PATH.read_text(encoding="utf-8")
        state, _, _ = pipeline.run_pipeline_to_step(raw_text, "demo.txt", up_to_step=7)

        dxf_file = tmp_path / "demo_output.dxf"
        export.export_dxf_bytes(state, output_path=dxf_file)
        assert dxf_file.exists()

        # Read back with ezdxf
        doc = ezdxf.readfile(str(dxf_file))
        auditor = doc.audit()
        assert len(auditor.errors) == 0, f"DXF audit errors: {auditor.errors}"
        assert len(auditor.fixes) == 0, f"DXF audit fixes: {auditor.fixes}"

        # Verify all required layers exist
        expected_layers = {
            "POINTS",
            "PT_NO",
            "PT_ELEV",
            "TIN",
            "CONTOUR_MAJOR",
            "CONTOUR_MINOR",
            "BREAKLINES",
            "BOUNDARY",
        }
        assert expected_layers.issubset({layer.dxf.name for layer in doc.layers})

        msp = doc.modelspace()
        point_entities = list(msp.query('POINT[layer=="POINTS"]'))
        assert len(point_entities) == len(state.active_points) == 216

        # Compare every point's XYZ coordinate against original global UTM coordinates
        for orig_pt, dxf_pt in zip(state.active_points, point_entities):
            loc = dxf_pt.dxf.location
            assert float(loc.x) == pytest.approx(orig_pt.easting, abs=1e-6)
            assert float(loc.y) == pytest.approx(orig_pt.northing, abs=1e-6)
            assert float(loc.z) == pytest.approx(orig_pt.elevation, abs=1e-6)

        # Verify 3DFACE entities on TIN layer match every filtered triangle's global XYZ
        face_entities = list(msp.query('3DFACE[layer=="TIN"]'))
        assert len(face_entities) == len(state.filtered_triangles) == 310
        verts = state.tin_vertices_local
        origin = state.origin
        for tri, face in zip(state.filtered_triangles, face_entities):
            for corner_idx, attr_name in enumerate(["vtx0", "vtx1", "vtx2"]):
                v_loc = verts[tri[corner_idx]]
                eg, ng, zg = origin.to_global(
                    float(v_loc[0]), float(v_loc[1]), float(v_loc[2])
                )
                f_vtx = getattr(face.dxf, attr_name)
                assert float(f_vtx.x) == pytest.approx(eg, abs=1e-6)
                assert float(f_vtx.y) == pytest.approx(ng, abs=1e-6)
                assert float(f_vtx.z) == pytest.approx(zg, abs=1e-6)

        # Also verify CSV export round-trip
        csv_text = export.export_csv_string(state)
        csv_lines = csv_text.strip().splitlines()
        assert len(csv_lines) == 217  # header + 216 points

        # Verify HTML report rendering
        html_report = report.render_html_report(state)
        assert 'dir="rtl"' in html_report
        assert 'lang="fa"' in html_report
        assert "@media print" in html_report


class TestSyntheticFixtures:
    """Tests for all 8 required synthetic fixtures."""

    def test_wide_grid_with_hill(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["wide_grid_hill"].read_text(encoding="utf-8")
        state, stats, _ = pipeline.run_pipeline_to_step(
            text,
            "wide_grid_hill.txt",
            up_to_step=7,
            step_params={5: {"max_edge_length": 25.0}, 6: {"interval": 1.0}},
        )
        # 100m x 100m grid -> exact plan area = 10,000 m2, 3D surface area > plan area
        assert stats["planimetric_area_m2"] == pytest.approx(10000.0, rel=1e-3)
        assert stats["surface_area_3d_m2"] > stats["planimetric_area_m2"]
        assert stats["prism_volume_net_m3"] > 1000.0
        assert len(state.contours) > 5

    def test_field_with_ditch_breakline(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["field_ditch"].read_text(encoding="utf-8")
        state, _stats, _ = pipeline.run_pipeline_to_step(
            text,
            "field_ditch.txt",
            up_to_step=7,
            step_params={
                3: {"code_roles": {"DITCH": "breakline", "FLD": "point"}},
                5: {"max_edge_length": 100.0},
            },
        )
        s4 = state.step_stats[4]
        assert s4["method"] == "scipy_constrained_breaklines"
        assert s4["constrained_edge_target_count"] == 2
        assert s4["constrained_edge_enforced_count"] == 2

        # Verify both ditch segments are actual edges in the triangulation
        edges = set()
        for t in state.tin_triangles:
            for k in range(3):
                u, v = int(t[k]), int(t[(k + 1) % 3])
                edges.add((min(u, v), max(u, v)))
        for u, v in state.breakline_edges:
            assert (min(u, v), max(u, v)) in edges

    def test_polygon_with_hole(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["polygon_hole"].read_text(encoding="utf-8")
        s1_state, _, _ = io.parse_survey_text(text, "polygon_hole.txt")
        # Define the inner 20m x 20m hole in local coordinates
        e0, n0 = 722000.0, 4029000.0
        hole_global = [
            (e0 + 20.0, n0 + 20.0),
            (e0 + 40.0, n0 + 20.0),
            (e0 + 40.0, n0 + 40.0),
            (e0 + 20.0, n0 + 40.0),
        ]
        hole_local = [s1_state.origin.to_local_xy(eg, ng) for eg, ng in hole_global]

        state, stats, _ = pipeline.run_pipeline_to_step(
            text,
            "polygon_hole.txt",
            up_to_step=7,
            step_params={
                3: {
                    "code_roles": {"BND": "boundary", "SRF": "point"},
                    "explicit_holes_local": [hole_local],
                },
                5: {"max_edge_length": 100.0, "use_boundary_polygon": True},
            },
        )
        # Outer 60x60 = 3600 m2, minus 20x20 hole = 3200 m2
        assert state.step_stats[5]["removed_by_boundary"] > 0
        assert stats["planimetric_area_m2"] == pytest.approx(3200.0, abs=1e-2)

    def test_duplicate_heavy_data(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["duplicates"].read_text(encoding="utf-8")
        state, _, _ = pipeline.run_pipeline_to_step(
            text,
            "duplicates.txt",
            up_to_step=7,
            step_params={
                2: {"duplicate_tolerance": 0.01},
                5: {"max_edge_length": 50.0},
            },
        )
        s2 = state.step_stats[2]
        assert s2["before_count"] == 38
        assert s2["duplicates_removed"] == 13
        assert s2["after_count"] == 25

    def test_noisy_outliers_data(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["outliers"].read_text(encoding="utf-8")
        state, _, _ = pipeline.run_pipeline_to_step(
            text,
            "outliers.txt",
            up_to_step=7,
            step_params={
                2: {"outlier_z_threshold": 3.5, "outlier_k_neighbors": 8},
                5: {"max_edge_length": 50.0},
            },
        )
        s2 = state.step_stats[2]
        assert s2["outliers_removed"] == 3
        assert s2["after_count"] == 49
        # Verify extreme elevation blunders were removed from active elevation range
        assert state.metrics["elevation_m"]["range"] < 2.0

    def test_ne_swapped_input(self, static_fixtures: dict[str, Path]) -> None:
        text = static_fixtures["ne_swapped"].read_text(encoding="utf-8")
        state, _, _ = pipeline.run_pipeline_to_step(
            text,
            "ne_swapped.txt",
            up_to_step=7,
            step_params={5: {"max_edge_length": 25.0}},
        )
        s1 = state.step_stats[1]
        assert s1["detected_format"]["ne_swapped_heuristic"] is True
        assert s1["detected_format"]["ne_swap_applied"] is True
        assert s1["extents"]["easting_min"] == pytest.approx(721900.0, abs=1e-3)
        assert s1["extents"]["northing_min"] == pytest.approx(4028800.0, abs=1e-3)

    def test_space_delimited_with_header(
        self, static_fixtures: dict[str, Path]
    ) -> None:
        text = static_fixtures["space_header"].read_text(encoding="utf-8")
        state, _, _ = pipeline.run_pipeline_to_step(
            text,
            "space_header.txt",
            up_to_step=7,
            step_params={5: {"max_edge_length": 25.0}},
        )
        s1 = state.step_stats[1]
        assert s1["detected_format"]["delimiter"] == "space"
        assert s1["detected_format"]["has_header"] is True
        assert s1["point_count"] == 25

    def test_200k_points_fixture_parses_and_triangulates(self) -> None:
        path_200k = ensure_200k_fixture()
        raw_text = path_200k.read_text(encoding="utf-8")
        state, s1, _ = io.parse_survey_text(raw_text, "survey_200k.txt")
        assert s1["point_count"] == 200_000
        state, s4, payload = pipeline.run_step(state, 4, {"honor_breaklines": False})
        assert s4["vertex_count"] == 200_000
        assert s4["triangle_count"] > 390_000
        assert payload["total_point_count"] == 200_000
