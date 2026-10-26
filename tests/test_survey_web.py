"""Integration tests for the FastAPI backend (`survey_web`)."""

from __future__ import annotations

import io as std_io
from pathlib import Path

import ezdxf
from fastapi.testclient import TestClient

from survey_web.app import create_app

ROOT_DIR = Path(__file__).parent.parent
DEMO_PATH = ROOT_DIR / "samples" / "demo.txt"


class TestSurveyWebAPI:
    """End-to-end API tests for session lifecycle, 7-step wizard, exports, and limits."""

    def test_healthz(self) -> None:
        client = TestClient(create_app())
        resp = client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["demo_available"] is True

    def test_demo_and_full_7_step_wizard_and_exports(self, tmp_path: Path) -> None:
        client = TestClient(create_app())

        # 1. Start demo session
        r_demo = client.post("/api/demo")
        assert r_demo.status_code == 200
        demo_data = r_demo.json()
        sid = demo_data["session_id"]
        assert demo_data["active_step"] == 1
        assert demo_data["stats"]["point_count"] == 216

        # 2. Run steps 2..7 sequentially
        r2 = client.post(
            f"/api/sessions/{sid}/steps/2",
            json={"duplicate_tolerance": 0.001, "outlier_z_threshold": 4.0},
        )
        assert r2.status_code == 200
        assert r2.json()["stats"]["after_count"] == 216

        r3 = client.post(
            f"/api/sessions/{sid}/steps/3",
            json={"code_roles": {"AF": "point", "J": "point", "END": "point"}},
        )
        assert r3.status_code == 200
        assert r3.json()["stats"]["active_point_count"] == 216

        r4 = client.post(
            f"/api/sessions/{sid}/steps/4", json={"honor_breaklines": True}
        )
        assert r4.status_code == 200
        assert r4.json()["stats"]["triangle_count"] == 418

        r5 = client.post(f"/api/sessions/{sid}/steps/5", json={"max_edge_length": 10.0})
        assert r5.status_code == 200
        assert r5.json()["stats"]["active_triangles_after"] == 310

        r6 = client.post(
            f"/api/sessions/{sid}/steps/6",
            json={"interval": 0.2, "major_multiplier": 5, "add_labels": True},
        )
        assert r6.status_code == 200
        assert r6.json()["stats"]["total_contour_polylines"] > 10

        r7 = client.post(f"/api/sessions/{sid}/steps/7", json={})
        assert r7.status_code == 200
        assert r7.json()["completed_steps"] == [1, 2, 3, 4, 5, 6, 7]

        # 3. Re-run an earlier step (e.g. step 5 with max_edge_length=15m) -> downstream steps 6, 7 invalidate
        r5_rerun = client.post(
            f"/api/sessions/{sid}/steps/5", json={"max_edge_length": 15.0}
        )
        assert r5_rerun.status_code == 200
        assert r5_rerun.json()["completed_steps"] == [1, 2, 3, 4, 5]

        # 4. State endpoint
        r_state = client.get(f"/api/sessions/{sid}/state")
        assert r_state.status_code == 200
        assert r_state.json()["session_id"] == sid

        # 5. Exports (DXF, CSV, Report)
        r_dxf = client.get(f"/api/sessions/{sid}/export/dxf")
        assert r_dxf.status_code == 200
        dxf_path = tmp_path / "api_out.dxf"
        dxf_path.write_bytes(r_dxf.content)
        doc = ezdxf.readfile(str(dxf_path))
        assert len(doc.audit().errors) == 0

        r_csv = client.get(f"/api/sessions/{sid}/export/csv")
        assert r_csv.status_code == 200
        assert "Northing,Easting,Elevation" in r_csv.text

        r_rep = client.get(f"/api/sessions/{sid}/export/report")
        assert r_rep.status_code == 200
        assert 'dir="rtl"' in r_rep.text

    def test_multipart_upload_and_limits(self, monkeypatch) -> None:
        client = TestClient(create_app())
        raw_bytes = DEMO_PATH.read_bytes()

        r_up = client.post(
            "/api/sessions",
            files={"file": ("demo.txt", std_io.BytesIO(raw_bytes), "text/plain")},
            data={"crs": "EPSG:32640"},
        )
        assert r_up.status_code == 200
        assert r_up.json()["stats"]["point_count"] == 216

        # Test point limit friendly error
        monkeypatch.setenv("MAX_POINTS", "50")
        r_too_many = client.post(
            "/api/sessions",
            files={"file": ("demo.txt", std_io.BytesIO(raw_bytes), "text/plain")},
        )
        assert r_too_many.status_code == 422
        assert "بیشتر از حد مجاز" in r_too_many.json()["detail"]

    def test_session_ttl_cleanup(self) -> None:
        # TTL of 0 minutes expires immediately on next check
        app_short = create_app(session_ttl_min=0.0)
        client = TestClient(app_short)
        r_demo = client.post("/api/demo")
        sid = r_demo.json()["session_id"]
        r_state = client.get(f"/api/sessions/{sid}/state")
        assert r_state.status_code == 404
