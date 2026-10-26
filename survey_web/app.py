"""FastAPI application serving the 7-step Persian topographic pipeline API and static UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from survey_core import export, io, pipeline, report
from survey_web.sessions import SessionStore

ROOT_DIR = Path(__file__).resolve().parent.parent
DEMO_FILE_PATH = ROOT_DIR / "samples" / "demo.txt"
STATIC_BUNDLE_DIR = Path(__file__).resolve().parent / "static_bundle"


def _get_limits() -> tuple[int, int]:
    """Read MAX_UPLOAD_MB and MAX_POINTS from environment variables."""
    max_mb = float(os.environ.get("MAX_UPLOAD_MB", "20"))
    max_pts = int(os.environ.get("MAX_POINTS", "200000"))
    return (int(max_mb * 1024 * 1024), max_pts)


def create_app(session_ttl_min: float | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    store = SessionStore(ttl_minutes=session_ttl_min)

    application = FastAPI(
        title="TopoConvert — سامانه مهندسی پردازش داده‌های نقشه‌برداری و توپوگرافی",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.state.session_store = store

    @application.get("/healthz")
    async def healthz() -> dict[str, Any]:
        """Render.com health check endpoint."""
        return {
            "status": "ok",
            "active_sessions": store.count(),
            "demo_available": DEMO_FILE_PATH.exists(),
        }

    @application.post("/api/sessions")
    async def create_session(request: Request) -> JSONResponse:
        """Upload a survey `.txt`/`.csv` file (multipart or JSON) and run Step 1 (`io`)."""
        max_bytes, max_points = _get_limits()
        content_type = request.headers.get("content-type", "")

        raw_bytes: bytes = b""
        filename = "survey.txt"
        params: dict[str, Any] = {"max_points": max_points}

        if "multipart/form-data" in content_type:
            form = await request.form()
            upload = form.get("file")
            if (
                upload is None
                or not isinstance(upload, UploadFile)
                and not hasattr(upload, "read")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="هیچ فایلی ارسال نشده است. لطفاً یک فایل .txt یا .csv انتخاب کنید.",
                )
            filename = getattr(upload, "filename", None) or "survey.txt"
            raw_bytes = await upload.read()  # type: ignore[union-attr]
            if form.get("crs"):
                params["crs"] = str(form["crs"])
            if "swap_ne" in form and form["swap_ne"] not in ("", "auto", None):
                params["swap_ne"] = str(form["swap_ne"]).lower() in ("true", "1", "yes")
            if form.get("delimiter"):
                params["delimiter"] = str(form["delimiter"])
        else:
            body_bytes = await request.body()
            if len(body_bytes) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"حجم فایل ارسالی بیش از حد مجاز ({max_bytes // (1024 * 1024)} مگابایت) است.",
                )
            try:
                data = await request.json()
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail="فرمت درخواست نامعتبر است.",
                ) from exc
            raw_text_in = str(data.get("raw_text", ""))
            raw_bytes = raw_text_in.encode("utf-8")
            filename = str(data.get("filename", "survey.txt"))
            if isinstance(data.get("params"), dict):
                params.update(data["params"])

        if len(raw_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="فایل بارگذاری‌شده خالی است.",
            )
        if len(raw_bytes) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"حجم فایل ({len(raw_bytes) / (1024 * 1024):.1f} مگابایت) بیش از حد مجاز ({max_bytes // (1024 * 1024)} مگابایت) است.",
            )

        try:
            raw_text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            raw_text = raw_bytes.decode("cp1256", errors="replace")

        try:
            state, stats, viewer_payload = io.parse_survey_text(
                raw_text=raw_text, filename=filename, params=params
            )
        except ValueError as exc:
            msg = str(exc)
            code = 422 if "بیشتر از حد مجاز" in msg else 400
            raise HTTPException(status_code=code, detail=msg) from exc

        rec = store.create(state, raw_bytes=raw_bytes)
        return JSONResponse(
            {
                "session_id": rec.session_id,
                "filename": state.filename,
                "active_step": 1,
                "completed_steps": state.completed_steps,
                "stats": stats,
                "step_stats": {str(k): v for k, v in state.step_stats.items()},
                "viewer_payload": viewer_payload,
            }
        )

    @application.post("/api/demo")
    async def create_demo_session(request: Request) -> JSONResponse:
        """Start a session from the bundled `samples/demo.txt` file."""
        if not DEMO_FILE_PATH.exists():
            raise HTTPException(
                status_code=404, detail="فایل نمونه (demo.txt) یافت نشد."
            )

        raw_bytes = DEMO_FILE_PATH.read_bytes()
        raw_text = raw_bytes.decode("utf-8-sig")
        display_name = "افتر_اقدسیه42_110047.txt"

        up_to_step = 1
        try:
            body = await request.body()
            if body:
                data = await request.json()
                if isinstance(data, dict) and "up_to_step" in data:
                    up_to_step = max(1, min(7, int(data["up_to_step"])))
        except (ValueError, TypeError):
            up_to_step = 1

        state, stats, viewer_payload = pipeline.run_pipeline_to_step(
            raw_text=raw_text,
            filename=display_name,
            up_to_step=up_to_step,
        )
        rec = store.create(state, raw_bytes=raw_bytes)
        return JSONResponse(
            {
                "session_id": rec.session_id,
                "filename": state.filename,
                "active_step": up_to_step,
                "completed_steps": state.completed_steps,
                "stats": stats,
                "step_stats": {str(k): v for k, v in state.step_stats.items()},
                "viewer_payload": viewer_payload,
            }
        )

    @application.post("/api/sessions/{session_id}/steps/{step_num}")
    async def execute_step(
        session_id: str, step_num: int, request: Request
    ) -> JSONResponse:
        """Run pipeline step `step_num` (1..7) with optional JSON parameters."""
        rec = store.get(session_id)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail="نشست مورد نظر یافت نشد یا منقضی شده است. لطفاً فایل را مجدداً بارگذاری کنید.",
            )

        params: dict[str, Any] = {}
        try:
            body = await request.body()
            if body:
                payload = await request.json()
                if isinstance(payload, dict):
                    if isinstance(payload.get("params"), dict):
                        params = dict(payload["params"])
                    else:
                        params = dict(payload)
        except (ValueError, TypeError):
            params = {}

        try:
            new_state, stats, viewer_payload = pipeline.run_step(
                rec.state, step_num, params
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        store.update(session_id, new_state, active_step=step_num)
        return JSONResponse(
            {
                "session_id": session_id,
                "step": step_num,
                "filename": new_state.filename,
                "active_step": step_num,
                "completed_steps": new_state.completed_steps,
                "stats": stats,
                "step_stats": {str(k): v for k, v in new_state.step_stats.items()},
                "viewer_payload": viewer_payload,
            }
        )

    @application.get("/api/sessions/{session_id}/state")
    async def get_session_state(
        session_id: str, step: int | None = None
    ) -> JSONResponse:
        """Return current session state, completed steps, stats, and viewer payload."""
        rec = store.get(session_id)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail="نشست مورد نظر یافت نشد یا منقضی شده است.",
            )
        state = rec.state
        active_step = step if step is not None and 1 <= step <= 7 else rec.active_step
        viewer_payload = io.build_viewer_payload_from_state(
            state, active_step=active_step
        )
        return JSONResponse(
            {
                "session_id": session_id,
                "filename": state.filename,
                "active_step": active_step,
                "completed_steps": state.completed_steps,
                "stats": state.step_stats.get(active_step, {}),
                "step_stats": {str(k): v for k, v in state.step_stats.items()},
                "viewer_payload": viewer_payload,
            }
        )

    @application.get("/api/sessions/{session_id}/export/{export_type}")
    async def export_artifact(session_id: str, export_type: str) -> Response:
        """Export CAD DXF (`dxf`), cleaned points CSV (`csv`), or printable HTML report (`report`)."""
        rec = store.get(session_id)
        if rec is None:
            raise HTTPException(
                status_code=404,
                detail="نشست مورد نظر یافت نشد یا منقضی شده است.",
            )

        fmt = export_type.lower().strip()
        if fmt not in ("dxf", "csv", "report"):
            raise HTTPException(
                status_code=400,
                detail=f"نوع خروجی نامعتبر است: {export_type} (مجاز: dxf, csv, report)",
            )

        state = rec.state
        # Ensure pipeline has run through step 7 so all layers/metrics are populated
        if 7 not in state.completed_steps:
            state, _, _ = pipeline.run_step(state, 7, {})
            store.update(session_id, state, active_step=rec.active_step)

        if fmt == "dxf":
            dxf_path = rec.temp_dir / "survey_export.dxf"
            dxf_bytes = export.export_dxf_bytes(state, output_path=dxf_path)
            return Response(
                content=dxf_bytes,
                media_type="application/dxf",
                headers={
                    "Content-Disposition": 'attachment; filename="topoconvert_survey.dxf"'
                },
            )

        if fmt == "csv":
            csv_text = export.export_csv_string(state)
            return Response(
                content=csv_text.encode("utf-8-sig"),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="topoconvert_cleaned.csv"'
                },
            )

        html_str = report.render_html_report(state)
        return HTMLResponse(content=html_str)

    # Mount static frontend bundle if built
    if STATIC_BUNDLE_DIR.exists():
        assets_dir = STATIC_BUNDLE_DIR / "assets"
        if assets_dir.exists():
            application.mount(
                "/assets", StaticFiles(directory=str(assets_dir)), name="assets"
            )
        fonts_dir = STATIC_BUNDLE_DIR / "fonts"
        if fonts_dir.exists():
            application.mount(
                "/fonts", StaticFiles(directory=str(fonts_dir)), name="fonts"
            )

    @application.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> Response:
        """Serve static frontend assets or fallback to SPA `index.html`."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="مسیر API یافت نشد.")

        if STATIC_BUNDLE_DIR.exists():
            candidate = (STATIC_BUNDLE_DIR / full_path).resolve()
            if (
                str(candidate).startswith(str(STATIC_BUNDLE_DIR.resolve()))
                and candidate.is_file()
            ):
                return FileResponse(str(candidate))
            index_file = STATIC_BUNDLE_DIR / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))

        return HTMLResponse(
            content=(
                '<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">'
                "<title>TopoConvert</title></head><body>"
                "<h1>سامانه TopoConvert آماده است</h1>"
                "</body></html>"
            )
        )

    return application


app = create_app()
