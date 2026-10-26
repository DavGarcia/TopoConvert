"""`survey_core/report.py`: Jinja2 Persian (RTL) HTML engineering report with print-ready A4 CSS."""

from __future__ import annotations

from typing import Any

import numpy as np
from jinja2 import BaseLoader, Environment

from survey_core.models import SurveyState

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_num(val: Any, decimals: int = 2) -> str:
    """Format a numeric or string value with Persian digits."""
    if isinstance(val, (int, np.integer)):
        s = f"{int(val):,}"
    elif isinstance(val, (float, np.floating)):
        s = f"{float(val):,.{decimals}f}"
    else:
        s = str(val)
    return s.translate(PERSIAN_DIGITS)


def _build_map_svg(state: SurveyState) -> str:
    """Generate an embedded vector SVG plan view of the filtered TIN and contours for the report."""
    verts = state.tin_vertices_local
    tris = (
        state.filtered_triangles
        if len(state.filtered_triangles) > 0
        else state.tin_triangles
    )
    if len(verts) == 0:
        return ""

    min_x, max_x = float(np.min(verts[:, 0])), float(np.max(verts[:, 0]))
    min_y, max_y = float(np.min(verts[:, 1])), float(np.max(verts[:, 1]))
    min_z, max_z = float(np.min(verts[:, 2])), float(np.max(verts[:, 2]))
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    span_z = max(max_z - min_z, 0.01)

    svg_w, svg_h = 640.0, 380.0
    pad = 28.0
    scale = min((svg_w - 2 * pad) / span_x, (svg_h - 2 * pad) / span_y)
    off_x = (svg_w - span_x * scale) / 2.0
    off_y = (svg_h - span_y * scale) / 2.0

    def tx(x: float) -> float:
        return off_x + (x - min_x) * scale

    def ty(y: float) -> float:
        return svg_h - (off_y + (y - min_y) * scale)

    parts: list[str] = [
        f'<svg viewBox="0 0 {int(svg_w)} {int(svg_h)}" class="report-svg" role="img" aria-label="نقشه پلان توپوگرافی">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#0f172a" rx="8"/>',
    ]

    # Draw filtered triangles (capped at 1500 in SVG for lightweight print rendering)
    step_tri = max(1, len(tris) // 1500)
    for t in tris[::step_tri]:
        p0, p1, p2 = verts[t[0]], verts[t[1]], verts[t[2]]
        z_norm = ((float(p0[2] + p1[2] + p2[2]) / 3.0) - min_z) / span_z
        r = int(30 + 160 * z_norm)
        g = int(130 + 70 * (1.0 - abs(z_norm - 0.5) * 2.0))
        b = int(210 - 130 * z_norm)
        pts_str = f"{tx(p0[0]):.1f},{ty(p0[1]):.1f} {tx(p1[0]):.1f},{ty(p1[1]):.1f} {tx(p2[0]):.1f},{ty(p2[1]):.1f}"
        parts.append(
            f'<polygon points="{pts_str}" fill="rgb({r},{g},{b})" fill-opacity="0.45" stroke="#334155" stroke-width="0.45"/>'
        )

    # Draw contours
    for c in state.contours[:400]:
        if len(c.points_local) < 2:
            continue
        d_str = " ".join(
            f"{'M' if idx == 0 else 'L'}{tx(px):.1f},{ty(py):.1f}"
            for idx, (px, py) in enumerate(c.points_local)
        )
        stroke = "#fbbf24" if c.is_major else "#94a3b8"
        sw = "1.3" if c.is_major else "0.65"
        parts.append(
            f'<path d="{d_str}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    # Draw points (capped at 600)
    pts_src = state.active_points or state.cleaned_points or state.raw_points
    step_pt = max(1, len(pts_src) // 600)
    for p in pts_src[::step_pt]:
        parts.append(
            f'<circle cx="{tx(p.x_local):.1f}" cy="{ty(p.y_local):.1f}" r="1.8" fill="#38bdf8"/>'
        )

    # North arrow
    parts.append(
        '<g transform="translate(595, 38)">'
        '<circle cx="0" cy="0" r="18" fill="#1e293b" stroke="#475569" stroke-width="1"/>'
        '<polygon points="0,-13 -5,7 0,3 5,7" fill="#38bdf8"/>'
        '<text x="0" y="15" text-anchor="middle" fill="#e2e8f0" font-size="9" font-weight="bold">N</text>'
        "</g>"
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _build_profile_svg(state: SurveyState) -> str:
    """Generate an embedded vector SVG longitudinal profile chart."""
    stations = (state.profile_data or {}).get("stations") or []
    if len(stations) < 2:
        return ""

    dists = [float(s["distance_m"]) for s in stations]
    z_means = [float(s["z_mean"]) for s in stations]
    z_mins = [float(s["z_min"]) for s in stations]
    z_maxs = [float(s["z_max"]) for s in stations]

    d_max = max(max(dists), 1.0)
    z_low = min(z_mins)
    z_high = max(z_maxs)
    z_span = max(z_high - z_low, 0.1)

    w, h = 640.0, 220.0
    pad_l, pad_r, pad_t, pad_b = 56.0, 24.0, 22.0, 36.0
    pw = w - pad_l - pad_r
    ph = h - pad_t - pad_b

    def sx(d: float) -> float:
        return pad_l + (d / d_max) * pw

    def sy(z: float) -> float:
        return pad_t + ph - ((z - z_low) / z_span) * ph

    poly_top = [f"{sx(d):.1f},{sy(zm):.1f}" for d, zm in zip(dists, z_maxs)]
    poly_bot = [
        f"{sx(d):.1f},{sy(zn):.1f}" for d, zn in reversed(list(zip(dists, z_mins)))
    ]
    band_pts = " ".join(poly_top + poly_bot)
    line_d = " ".join(
        f"{'M' if i == 0 else 'L'}{sx(d):.1f},{sy(z):.1f}"
        for i, (d, z) in enumerate(zip(dists, z_means))
    )

    parts = [
        f'<svg viewBox="0 0 {int(w)} {int(h)}" class="report-svg" role="img" aria-label="پروفیل طولی مسیر">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#0f172a" rx="8"/>',
        f'<polygon points="{band_pts}" fill="#38bdf8" fill-opacity="0.16"/>',
        f'<path d="{line_d}" fill="none" stroke="#38bdf8" stroke-width="2.2"/>',
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#475569" stroke-width="1"/>',
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#475569" stroke-width="1"/>',
        f'<text x="{pad_l-6}" y="{pad_t+8}" text-anchor="end" fill="#cbd5e1" font-size="10">{to_fa_num(z_high, 2)}m</text>',
        f'<text x="{pad_l-6}" y="{pad_t+ph}" text-anchor="end" fill="#cbd5e1" font-size="10">{to_fa_num(z_low, 2)}m</text>',
        f'<text x="{pad_l}" y="{h-10}" text-anchor="start" fill="#cbd5e1" font-size="10">۰m</text>',
        f'<text x="{pad_l+pw}" y="{h-10}" text-anchor="end" fill="#cbd5e1" font-size="10">{to_fa_num(d_max, 1)}m</text>',
        "</svg>",
    ]
    return "\n".join(parts)


REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>گزارش فنی توپوگرافی — {{ filename }}</title>
  <style>
    :root {
      --bg: #0b1120;
      --card: #111827;
      --border: #1e293b;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --warn: #f59e0b;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      padding: 0;
      font-family: "Vazirmatn", "Tahoma", sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.65;
      overflow-x: hidden;
    }
    .container {
      max-width: 960px;
      margin: 0 auto;
      padding: 20px 16px 40px;
    }
    .header-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    h1 {
      font-size: clamp(1.2rem, 2.5vw, 1.65rem);
      margin: 0 0 6px 0;
      color: var(--accent);
    }
    h2 {
      font-size: clamp(1.02rem, 2vw, 1.25rem);
      margin: 0 0 12px 0;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
      color: #e2e8f0;
    }
    .meta {
      font-size: 0.88rem;
      color: var(--muted);
    }
    .print-btn {
      background: var(--accent);
      color: #0f172a;
      border: none;
      border-radius: 8px;
      padding: 10px 18px;
      font-weight: 700;
      font-family: inherit;
      cursor: pointer;
      min-height: 44px;
    }
    .section-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 18px;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
    }
    .metric-box {
      background: rgba(30, 41, 59, 0.55);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 14px;
    }
    .metric-label {
      font-size: 0.82rem;
      color: var(--muted);
      margin-bottom: 4px;
    }
    .metric-value {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text);
    }
    .explanation-box {
      background: rgba(245, 158, 11, 0.12);
      border-right: 4px solid var(--warn);
      border-radius: 8px;
      padding: 14px;
      font-size: 0.92rem;
      margin-top: 12px;
    }
    .table-wrap {
      width: 100%;
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }
    th, td {
      border: 1px solid var(--border);
      padding: 8px 10px;
      text-align: right;
    }
    th {
      background: rgba(30, 41, 59, 0.8);
      color: var(--accent);
    }
    .report-svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 8px;
    }
    @media (max-width: 768px) {
      .metrics-grid {
        grid-template-columns: 1fr;
      }
      .header-card {
        flex-direction: column;
        align-items: stretch;
      }
    }
    @media print {
      @page { size: A4; margin: 12mm; }
      body {
        background: #ffffff !important;
        color: #0f172a !important;
      }
      .print-btn { display: none !important; }
      .header-card, .section-card, .metric-box {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        break-inside: avoid;
      }
      h1, h2, th, .metric-value { color: #0f172a !important; }
      .meta, .metric-label { color: #475569 !important; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <div>
        <h1>گزارش مهندسی پردازش توپوگرافی و مدل رقومی ارتفاع (TIN)</h1>
        <div class="meta">
          فایل ورودی: <strong>{{ filename }}</strong> |
          سیستم تصویر: <strong>{{ crs }} ({{ crs_name }})</strong>
          {% if crs_is_assumed %}<span style="color:#f59e0b;">[فرض پیش‌فرض — تایید توسط کاربر توصیه می‌شود]</span>{% endif %}
        </div>
        <div class="meta">
          مبدأ محلی محاسبات: E₀={{ origin_e0 }}m ، N₀={{ origin_n0 }}m ، Z₀={{ origin_z0 }}m
        </div>
      </div>
      <button class="print-btn" onclick="window.print()">چاپ / ذخیره PDF (A4)</button>
    </div>

    <div class="section-card">
      <h2>۱. خلاصه شاخص‌های هندسی و حجمی</h2>
      <div class="metrics-grid">
        <div class="metric-box">
          <div class="metric-label">تعداد نقاط (خام / پاک‌سازی / فعال)</div>
          <div class="metric-value">{{ pt_raw }} / {{ pt_clean }} / {{ pt_active }}</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">مساحت افقی (فیلترشده)</div>
          <div class="metric-value">{{ plan_area }} مترمربع</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">مساحت سه‌بعدی سطح (فیلترشده)</div>
          <div class="metric-value">{{ surf_area_3d }} مترمربع</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">مساحت افقی مثلث‌بندی خام (بدون فیلتر)</div>
          <div class="metric-value">{{ unfilt_plan_area }} مترمربع</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">حجم منشوری نسبت به تراز مبنا ({{ ref_elev }}m)</div>
          <div class="metric-value">{{ prism_vol }} مترمکعب</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">کمینه / میانگین / بیشینه ارتفاع (Z)</div>
          <div class="metric-value">{{ z_min }} / {{ z_mean }} / {{ z_max }} متر</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">شیب میانگین / بیشینه سطح</div>
          <div class="metric-value">{{ slope_mean_deg }}° ({{ slope_mean_pct }}٪) / {{ slope_max_deg }}°</div>
        </div>
        <div class="metric-box">
          <div class="metric-label">طول مسیر محوری / تعداد منحنی میزان</div>
          <div class="metric-value">{{ path_len }} متر / {{ contour_count }} خط</div>
        </div>
      </div>

      <div class="explanation-box">
        <strong>تحلیل فنی اثر فیلتر طول ضلع بر مساحت مثلث‌بندی:</strong><br/>
        {{ strip_explanation }}
      </div>
    </div>

    {% if map_svg %}
    <div class="section-card">
      <h2>۲. نقشه پلان شبکه مثلثی (TIN) و منحنی‌های میزان</h2>
      {{ map_svg | safe }}
    </div>
    {% endif %}

    {% if profile_svg %}
    <div class="section-card">
      <h2>۳. پروفیل طولی مسیر برداشت</h2>
      {{ profile_svg | safe }}
    </div>
    {% endif %}

    <div class="section-card">
      <h2>۴. جدول کدهای برداشت و نقش خطوط</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>کد برداشت</th>
              <th>تعداد نقاط</th>
              <th>نقش انتخاب‌شده</th>
              <th>رنگ لایه</th>
            </tr>
          </thead>
          <tbody>
            {% for c in codes %}
            <tr>
              <td><strong>{{ c.code }}</strong></td>
              <td>{{ c.count_fa }}</td>
              <td>{{ c.role_fa }}</td>
              <td><span style="display:inline-block;width:14px;height:14px;background:{{ c.color }};border-radius:3px;vertical-align:middle;"></span> {{ c.color }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>
"""

ROLE_LABELS_FA = {
    "point": "نقطه عادی سطح (Surface Point)",
    "breakline": "خط شکست (Breakline)",
    "boundary": "مرز محدوده (Boundary)",
    "ignore": "نادیده گرفته‌شده (Ignore)",
}


def render_html_report(state: SurveyState) -> str:
    """Render a complete, print-ready Persian RTL HTML report from `state`."""
    m = state.metrics or {}
    elev = m.get("elevation_m") or {"min": 0.0, "max": 0.0, "mean": 0.0}
    slope = m.get("slope") or {"mean_deg": 0.0, "max_deg": 0.0, "mean_pct": 0.0}

    codes_rows = [
        {
            "code": cfg.code,
            "count_fa": to_fa_num(cfg.count, 0),
            "role_fa": ROLE_LABELS_FA.get(cfg.role, cfg.role),
            "color": cfg.color,
        }
        for cfg in state.code_configs.values()
    ]

    env = Environment(loader=BaseLoader(), autoescape=True)
    tmpl = env.from_string(REPORT_TEMPLATE)
    return tmpl.render(
        filename=state.filename,
        crs=state.crs,
        crs_name=state.crs_name,
        crs_is_assumed=state.crs_is_assumed,
        origin_e0=to_fa_num(state.origin.e0, 3),
        origin_n0=to_fa_num(state.origin.n0, 3),
        origin_z0=to_fa_num(state.origin.z0, 3),
        pt_raw=to_fa_num(m.get("point_count_raw", len(state.raw_points)), 0),
        pt_clean=to_fa_num(m.get("point_count_cleaned", len(state.cleaned_points)), 0),
        pt_active=to_fa_num(m.get("point_count_active", len(state.active_points)), 0),
        plan_area=to_fa_num(m.get("planimetric_area_m2", 0.0), 2),
        surf_area_3d=to_fa_num(m.get("surface_area_3d_m2", 0.0), 2),
        unfilt_plan_area=to_fa_num(m.get("unfiltered_planimetric_area_m2", 0.0), 2),
        ref_elev=to_fa_num(m.get("reference_elevation_m", state.origin.z0), 3),
        prism_vol=to_fa_num(m.get("prism_volume_net_m3", 0.0), 2),
        z_min=to_fa_num(elev.get("min", 0.0), 3),
        z_mean=to_fa_num(elev.get("mean", 0.0), 3),
        z_max=to_fa_num(elev.get("max", 0.0), 3),
        slope_mean_deg=to_fa_num(slope.get("mean_deg", 0.0), 2),
        slope_mean_pct=to_fa_num(slope.get("mean_pct", 0.0), 2),
        slope_max_deg=to_fa_num(slope.get("max_deg", 0.0), 2),
        path_len=to_fa_num(m.get("path_length_m", 0.0), 1),
        contour_count=to_fa_num(m.get("contour_count", len(state.contours)), 0),
        strip_explanation=to_fa_num(m.get("strip_geometry_explanation", "")),
        map_svg=_build_map_svg(state),
        profile_svg=_build_profile_svg(state),
        codes=codes_rows,
    )
