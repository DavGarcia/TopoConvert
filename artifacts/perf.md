# Performance Benchmark Report (`artifacts/perf.md`)

## 1. Benchmark Methodology
All benchmarks were executed on the sandbox environment (Python 3.11.2, SciPy `Delaunay` + `cKDTree`, NumPy vectorized geometry kernels) using `time.perf_counter()` and `tracemalloc` across all 7 steps of `survey_core`:

1. **Dataset A (`samples/demo.txt`)**: Real 216-point total-station/GNSS corridor survey (`افتر اقدسیه42_110047.txt`), ~404.2 m corridor path length, codes `AF` (211), `J` (4), `END` (1).
2. **Dataset B (`synth_100k.txt`)**: Synthetic 100,000-point survey dataset (~199,900 Delaunay triangles) in UTM Zone 40N (`Easting` 721,600–722,600 m, `Northing` 4,028,600–4,029,600 m).

---

## 2. Step-by-Step Runtime & Memory Results

| Pipeline Step | Module | `demo.txt` (216 pts) | `synth_100k.txt` (100,000 pts) | Algorithmic Complexity & Optimization |
| :--- | :--- | :---: | :---: | :--- |
| **Step 1: Parse & Local Origin Shift** | `survey_core.io` | `18.18 ms` | `6,716.0 ms` | Auto-delimiter/header/N-E detection + local origin subtraction $(E_0, N_0, Z_0)$ |
| **Step 2: Duplicate & Outlier Clean** | `survey_core.clean` | `7.55 ms` | `2,091.9 ms` | Vectorized `cKDTree.query_pairs` + vectorized $(N \times k)$ MAD/z-score matrix (**14.5× speedup** over per-point loop) |
| **Step 3: Code Roles & Breaklines** | `survey_core.codes` | `4.18 ms` | `579.7 ms` | Single-pass code grouping & breakline polyline assembly |
| **Step 4: Constrained Delaunay TIN** | `survey_core.tin` | `15.86 ms` | `1,643.4 ms` | `scipy.spatial.Delaunay` in local coordinates + Sloan edge-recovery flip pass + vectorized 2D/3D triangle areas & slopes |
| **Step 5: Max-Edge & Boundary Filter** | `survey_core.filt` | `37.07 ms` | `1,043.1 ms` | Vectorized edge-length/min-angle boolean mask + `matplotlib.path.Path.contains_points` |
| **Step 6: Contours & Slope Heatmap** | `survey_core.contour` | `42.64 ms` | `3,725.5 ms` | Vectorized active-triangle edge-plane intersection + quantized $(1\text{ mm})$ endpoint chaining |
| **Step 7: Engineering Metrics & Profile** | `survey_core.metrics` | `24.74 ms` | `1,097.2 ms` | Vectorized truncated-prism volume, area-weighted slope statistics & centerline corridor stations |
| **Total End-to-End (Steps 1–7)** | `survey_core.pipeline` | **`150.37 ms`** | **`16,897.0 ms` (`16.9 s`)** | Sub-200ms interactive response on standard surveys; <17s full 7-step batch on 100k points |
| **Peak Traced Memory (`tracemalloc`)** | — | **`1.07 MB`** | **`149.51 MB`** | Compact `float64` NumPy arrays + decimated `points_flat` viewer buffer |

---

## 3. Viewer & Payload Optimizations for Large Point Clouds (100k–200k Points)
- **Flat Coordinate Array (`points_flat`)**: When `len(points) > 3,000`, `survey_core.io.build_viewer_payload_from_state` emits a flat `[x, y, z, ...]` numeric buffer alongside a capped inspection sample so JSON serialization and browser parsing remain fast (`< 150 ms`).
- **60 FPS Live Edge Filtering in Step 5**: `TopoViewer.tsx` pre-receives `all_triangles`, `max_edges`, `min_angles`, `plan_areas`, and `areas_3d` in Step 4/5 so dragging the `max_edge_length` slider filters triangles and recalculates planimetric (`1,028.39 m²`) and 3D surface (`1,080.42 m²`) areas on the client in **`< 2 ms` per frame** before committing to the server.
