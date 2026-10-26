"""Synthetic survey fixture generators for `survey_core` tests.

Generates and persists the 8 required synthetic fixtures in `tests/fixtures/`:
1. `survey_wide_grid_hill.txt`: Wide grid with a Gaussian hill
2. `survey_field_ditch_breakline.txt`: Field with a sharp ditch (breakline code `DITCH`)
3. `survey_polygon_hole.txt`: Polygon with an interior hole
4. `survey_duplicates.txt`: Duplicate-heavy survey dataset
5. `survey_noisy_outliers.txt`: Survey dataset with extreme elevation outliers
6. `survey_ne_swapped.txt`: N/E swapped UTM coordinates (`ID,Code,Easting,Northing,Z`)
7. `survey_space_header.txt`: Space-delimited file with header row
8. `survey_200k.txt`: 200,000-point synthetic dataset for performance and memory testing
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np

FIXTURES_DIR = Path(__file__).parent


def generate_wide_grid_with_hill() -> str:
    """11x11 regular grid (100m x 100m) in UTM with a smooth 10m hill in the center."""
    e0, n0, z0 = 722000.0, 4029000.0, 1000.0
    lines = []
    pid = 1
    for iy in range(11):
        for ix in range(11):
            x = ix * 10.0
            y = iy * 10.0
            r2 = (x - 50.0) ** 2 + (y - 50.0) ** 2
            z = z0 + 10.0 * math.exp(-r2 / 600.0)
            lines.append(f"{pid},GRD,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
            pid += 1
    return "\n".join(lines) + "\n"


def generate_field_with_ditch_breakline() -> str:
    """Flat field at Z=1000m with a diagonal V-ditch at Z=997m marked with code `DITCH`."""
    e0, n0 = 722000.0, 4029000.0
    lines = []
    pid = 1
    # Bank and field points
    field_pts = [
        (0.0, 0.0, 1000.0, "FLD"),
        (50.0, 0.0, 1000.0, "FLD"),
        (50.0, 50.0, 1000.0, "FLD"),
        (0.0, 50.0, 1000.0, "FLD"),
        (10.0, 30.0, 1000.0, "FLD"),
        (40.0, 20.0, 1000.0, "FLD"),
        (20.0, 40.0, 1000.0, "FLD"),
        (30.0, 10.0, 1000.0, "FLD"),
    ]
    for x, y, z, code in field_pts:
        lines.append(f"{pid},{code},{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
        pid += 1

    # Ditch breakline running diagonally from (10,10) to (40,40) at Z=997.0
    ditch_pts = [
        (10.0, 10.0, 997.0),
        (25.0, 25.0, 997.0),
        (40.0, 40.0, 997.0),
    ]
    for x, y, z in ditch_pts:
        lines.append(f"{pid},DITCH,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
        pid += 1

    return "\n".join(lines) + "\n"


def generate_polygon_with_hole() -> str:
    """Outer 60m x 60m boundary (`BND`) with an inner 20m x 20m void hole."""
    e0, n0, z0 = 722000.0, 4029000.0, 1010.0
    lines = []
    pid = 1
    # Outer boundary ring (CCW)
    bnd = [(0.0, 0.0), (60.0, 0.0), (60.0, 60.0), (0.0, 60.0)]
    for x, y in bnd:
        z = z0 + 0.02 * x + 0.01 * y
        lines.append(f"{pid},BND,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
        pid += 1

    # Grid points excluding interior hole (20 < x < 40 and 20 < y < 40)
    for iy in range(0, 61, 10):
        for ix in range(0, 61, 10):
            if (ix, iy) in [(0, 0), (60, 0), (60, 60), (0, 60)]:
                continue
            if 20 < ix < 40 and 20 < iy < 40:
                continue
            z = z0 + 0.02 * ix + 0.01 * iy
            lines.append(f"{pid},SRF,{n0 + iy:.3f},{e0 + ix:.3f},{z:.3f}")
            pid += 1
    return "\n".join(lines) + "\n"


def generate_duplicate_heavy_data() -> str:
    """Grid with exact and near-exact (< 2mm) duplicate points."""
    e0, n0, z0 = 722000.0, 4029000.0, 1020.0
    lines = []
    pid = 1
    for iy in range(5):
        for ix in range(5):
            x = ix * 10.0
            y = iy * 10.0
            z = z0 + 0.5 * ix + 0.3 * iy
            lines.append(f"{pid},PT,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
            pid += 1
            # Add duplicate within 0.0005m for even indices
            if (ix + iy) % 2 == 0:
                lines.append(f"{pid},PT,{n0 + y + 0.0003:.4f},{e0 + x + 0.0003:.4f},{z:.3f}")
                pid += 1
    return "\n".join(lines) + "\n"


def generate_noisy_outliers_data() -> str:
    """Smooth terrain with 3 extreme elevation blunder points (+45m, -38m, +60m)."""
    e0, n0, z0 = 722000.0, 4029000.0, 1005.0
    lines = []
    pid = 1
    for iy in range(7):
        for ix in range(7):
            x = ix * 8.0
            y = iy * 8.0
            z = z0 + 0.1 * ix + 0.1 * iy
            lines.append(f"{pid},PT,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
            pid += 1
    # Inject 3 unmistakable total-station prism height blunders
    blunders = [
        (16.5, 16.5, z0 + 45.0),
        (32.5, 24.5, z0 - 38.0),
        (24.5, 40.5, z0 + 60.0),
    ]
    for x, y, z in blunders:
        lines.append(f"{pid},PT,{n0 + y:.3f},{e0 + x:.3f},{z:.3f}")
        pid += 1
    return "\n".join(lines) + "\n"


def generate_ne_swapped_input() -> str:
    """Survey file where Col 3 is Easting (~721,900) and Col 4 is Northing (~4,028,800)."""
    e0, n0, z0 = 721900.0, 4028800.0, 1050.0
    lines = []
    pid = 1
    for iy in range(5):
        for ix in range(5):
            e = e0 + ix * 5.0
            n = n0 + iy * 5.0
            z = z0 + 0.2 * ix + 0.15 * iy
            # Intentionally swapped: Easting in col 3, Northing in col 4
            lines.append(f"{pid},AF,{e:.3f},{n:.3f},{z:.3f}")
            pid += 1
    return "\n".join(lines) + "\n"


def generate_space_delimited_with_header() -> str:
    """Space-delimited survey file with a header line."""
    e0, n0, z0 = 721800.0, 4028700.0, 1040.0
    lines = ["ID Code Northing Easting Elevation"]
    pid = 1
    for iy in range(5):
        for ix in range(5):
            e = e0 + ix * 6.0
            n = n0 + iy * 6.0
            z = z0 + 0.25 * ix + 0.1 * iy
            lines.append(f"{pid} TOPO {n:.3f} {e:.3f} {z:.3f}")
            pid += 1
    return "\n".join(lines) + "\n"


def ensure_static_fixtures() -> dict[str, Path]:
    """Write the 7 compact synthetic fixture files to `tests/fixtures/`."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "wide_grid_hill": (FIXTURES_DIR / "survey_wide_grid_hill.txt", generate_wide_grid_with_hill),
        "field_ditch": (FIXTURES_DIR / "survey_field_ditch_breakline.txt", generate_field_with_ditch_breakline),
        "polygon_hole": (FIXTURES_DIR / "survey_polygon_hole.txt", generate_polygon_with_hole),
        "duplicates": (FIXTURES_DIR / "survey_duplicates.txt", generate_duplicate_heavy_data),
        "outliers": (FIXTURES_DIR / "survey_noisy_outliers.txt", generate_noisy_outliers_data),
        "ne_swapped": (FIXTURES_DIR / "survey_ne_swapped.txt", generate_ne_swapped_input),
        "space_header": (FIXTURES_DIR / "survey_space_header.txt", generate_space_delimited_with_header),
    }
    paths: dict[str, Path] = {}
    for key, (path, fn) in files.items():
        path.write_text(fn(), encoding="utf-8")
        paths[key] = path
    return paths


def ensure_200k_fixture(target_path: Path | None = None) -> Path:
    """Generate a deterministic 200,000-point survey file on disk."""
    path = target_path or (FIXTURES_DIR / "survey_200k.txt")
    if path.exists() and path.stat().st_size > 4_000_000:
        return path

    rng = np.random.default_rng(42)
    n_pts = 200_000
    # 500 x 400 perturbed grid
    gx, gy = np.meshgrid(
        np.linspace(0.0, 1000.0, 500),
        np.linspace(0.0, 800.0, 400),
    )
    x = gx.ravel() + rng.uniform(-0.2, 0.2, size=n_pts)
    y = gy.ravel() + rng.uniform(-0.2, 0.2, size=n_pts)
    z = 1050.0 + 5.0 * np.sin(x / 120.0) * np.cos(y / 120.0)
    e = 721000.0 + x
    n = 4028000.0 + y

    ids = np.arange(1, n_pts + 1)
    chunks = [
        f"{i},AF,{nv:.2f},{ev:.2f},{zv:.2f}"
        for i, nv, ev, zv in zip(ids, n, e, z)
    ]
    path.write_text("\n".join(chunks) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    ensure_static_fixtures()
    ensure_200k_fixture()
