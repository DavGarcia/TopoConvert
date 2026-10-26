# TopoConvert Architecture (`ARCHITECTURE.md`)

## 1. High-Level Package Structure

The repository is organized into four cleanly separated layers so the existing `topoconvert` CLI remains 100% backward-compatible while powering the new 7-step interactive Persian (RTL) topographic survey web application:

```text
TopoConvert/
├── topoconvert/          # Original CLI & KML/CSV/DXF conversion commands (preserved intact)
├── survey_core/          # Pure-Python, stateless 7-step survey pipeline (projected meters, zero web imports)
│   ├── models.py         # Immutable dataclasses (SurveyPoint, LocalOrigin, TinData, SurveyState)
│   ├── io.py             # Step 1: Delimiter/header/N-E swap auto-detection & local origin shift
│   ├── clean.py          # Step 2: Vectorized cKDTree duplicate removal & local MAD z-score outlier filter
│   ├── codes.py          # Step 3: Explicit survey code role assignment (point/breakline/boundary/ignore)
│   ├── tin.py            # Step 4: Delaunay TIN + Sloan constrained breakline edge-flipping & densification
│   ├── filt.py           # Step 5: Max-edge length, min-angle & boundary polygon triangle filtering
│   ├── contour.py        # Step 6: Direct TIN triangle-plane contour slicing, chaining & slope heatmap
│   ├── metrics.py        # Step 7: Planimetric/3D areas, truncated-prism volume & longitudinal profile
│   ├── export.py         # AutoCAD R2010 DXF (ezdxf audited) & cleaned CSV exporters in global UTM coords
│   ├── report.py         # Self-contained printable RTL Persian HTML/A4 PDF engineering report
│   └── pipeline.py       # Pure step dispatcher: run_step(state, step_num, params) -> (new_state, stats, payload)
├── survey_web/           # FastAPI backend & TTL session store
│   ├── sessions.py       # Thread-safe in-memory + temp-dir session store (2h TTL, 20MB / 200k point caps)
│   ├── app.py            # REST endpoints (/api/sessions, /api/demo, /steps/{n}, /export/*, /healthz) + SPA host
│   └── static_bundle/    # Compiled production React+TS+Vite frontend & self-hosted Vazirmatn fonts
└── frontend/             # Mobile-first RTL Persian React 18 + TypeScript + Three.js/Canvas SPA
    ├── public/fonts/     # Self-hosted Vazirmatn-{Regular,Medium,SemiBold,Bold}.woff2 (zero external CDNs)
    └── src/
        ├── i18n/fa.json  # Complete Persian engineering terminology dictionary
        ├── components/   # TopoViewer.tsx (2D Canvas + 3D Three.js) & ProfileChart.tsx (SVG corridor profile)
        └── App.tsx       # 7-step wizard, mobile draggable bottom sheet, desktop collapsible right panel
```

---

## 2. Coordinate Convention & Local-Origin Numerical Stability

### 2.1 Surveying Coordinate Convention
Total-station and GNSS survey files in Iran and standard engineering practice record rows as:
$$\text{ID}, \text{Code}, \text{Northing } (N), \text{Easting } (E), \text{Elevation } (Z)$$
For example, row 1 of `samples/demo.txt`:
```text
1,AF,4028664.449,721956.404,1056.441
```
- **Cartesian Mapping**: $X = \text{Easting } (E)$, $Y = \text{Northing } (N)$, $Z = \text{Elevation}$.
- **Heuristic $N/E$ Detection**: In UTM northern-hemisphere mid-latitude zones (such as Zone 38N–41N), Northing $N \in [10^6, 10^7]\text{ m}$ and Easting $E \in [1.6 \times 10^5, 8.4 \times 10^5]\text{ m}$. `survey_core.io` automatically detects whether column 3 is Northing or Easting, flags any swap in `detected_format`, and exposes a manual **«جابجایی ستون N و E»** override in Step 1.
- **Never Silently Guess Policy**:
  - Default CRS is set to `EPSG:32640` (WGS 84 / UTM Zone 40N) and explicitly badged as an **unconfirmed assumption** in Step 1 until confirmed or changed by the user.
  - Survey point codes (`AF`, `J`, `END`, etc.) default to `point` role and display a mandatory engineering warning banner in Step 3 so the user explicitly assigns `breakline`, `boundary`, or `ignore` roles.

### 2.2 Local Origin Shift $(E_0, N_0, Z_0)$
Computing Delaunay circumcircles, triangle cross products, or prism volumes directly on raw UTM coordinates ($N \approx 4,028,800\text{ m}$) causes IEEE-754 float64 precision loss when squaring coordinate differences at millimeter scale.
- In Step 1 (`survey_core.io`), we compute the dataset origin:
  $$E_0 = \min(E), \quad N_0 = \min(N), \quad Z_0 = \min(Z)$$
- Every internal computation (Steps 2–7) operates in local meter coordinates:
  $$x = E - E_0, \quad y = N - N_0, \quad z = Z - Z_0$$
- On export (`survey_core.export` for CAD DXF and CSV, `survey_core.report` for HTML/PDF, and point inspection in `TopoViewer`), global coordinates are restored via:
  $$E = x + E_0, \quad N = y + N_0, \quad Z = z + Z_0$$

---

## 3. Narrow Corridor Geometry & Why Step 5 Edge Filtering Matters

On `samples/demo.txt` (`افتر اقدسیه42_110047.txt`, 216 points):
- The survey captures a narrow (~2.5 m wide), gently curving ~404.2 m corridor (`Easting` span `281.78 m`, `Northing` span `302.90 m`, elevation `1055.165 m` to `1056.636 m`).
- **Step 4 (Unfiltered Delaunay TIN)**: Triangulating the convex hull produces **418 triangles**, including 108 long exterior chord triangles that bridge across concave bends of the strip. This inflates the unfiltered planimetric area to **`2,297.49 m²`** (`2,471.65 m²` 3D surface area) — a **2.23× artificial inflation**.
- **Step 5 (Filtered TIN, `max_edge_length = 10.0 m`)**: Removing triangles with any edge $> 10.0\text{ m}$ strips away all 108 exterior bridging triangles while preserving all **310 physical corridor triangles**, yielding the true corridor planimetric area of **`1,028.39 m²`** and 3D surface area of **`1,080.42 m²`**.

---

## 4. Dependency & License Audit (100% MIT / BSD / Apache-2.0 Compatible)

Per project constraints, every runtime dependency was audited for MIT compatibility prior to inclusion:

| Package | Version | License | Role & Audit Note |
| :--- | :--- | :--- | :--- |
| `scipy` | `>=1.9.0` | **BSD-3-Clause** | Used for `scipy.spatial.Delaunay` and `cKDTree`. **Note on `triangle` & `civpy`**: PyPI `triangle` is licensed under **LGPL-3.0** (wrapping Jonathan Shewchuk's non-commercial Triangle C library), and `civpy` is not published on PyPI (HTTP 404). To maintain strict MIT compatibility, `triangle` was excluded; `survey_core/tin.py` implements constrained breakline recovery via Sloan edge-flipping and `civpy`-style breakline densification on top of `scipy.spatial.Delaunay`. |
| `numpy` | `>=1.21.0` | **BSD-3-Clause** | Vectorized local-coordinate geometry, areas, slopes, and prism volumes. |
| `ezdxf` | `>=1.0.0` | **MIT** | AutoCAD R2010 `.dxf` generation (`SURVEY_POINTS`, `BREAKLINES`, `BOUNDARY`, `TIN_FACES`, `CONTOURS_MINOR`, `CONTOURS_MAJOR`, `CONTOUR_LABELS`) with zero `ezdxf.audit()` errors. |
| `pyproj` | `>=3.3.0` | **MIT** | CRS validation and UTM coordinate projection. |
| `matplotlib` | `>=3.5.0` | **PSF / BSD-compatible** | `matplotlib.path.Path` for vectorized polygon boundary containment. |
| `fastapi` | `>=0.100.0` | **MIT** | REST API and static SPA server (`survey_web/app.py`). |
| `uvicorn` | `>=0.23.0` | **BSD-3-Clause** | ASGI production server. |
| `python-multipart` | `>=0.0.6` | **Apache-2.0** | Multipart `.txt`/`.csv` survey file uploads. |
| `react` / `react-dom` | `^18.3.1` | **MIT** | Frontend 7-step wizard UI. |
| `three` | `^0.170.0` | **MIT** | Interactive 3D terrain mesh, wireframe, and draped contours viewer. |
| `vazirmatn` | `^33.003` | **OFL-1.1** | Self-hosted Persian webfont (`Vazirmatn-*.woff2` served locally from `/fonts/`). |
