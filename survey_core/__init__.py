"""Pure-Python topographic survey processing core package (`survey_core`).

Provides a 7-step functional pipeline for total-station and GNSS survey files:
1. io: Parse, validate, and auto-detect delimiter, header, N/E order, and CRS
2. clean: KD-tree duplicate removal and local z-score elevation outlier removal
3. codes: Survey code classification (point / breakline / boundary / ignore)
4. tin: Delaunay TIN with constrained breakline edge enforcement
5. filt: Triangle filtering by max edge length, min angle, and boundary polygon
6. contour: Marching-triangles contour generation (minor/major, labels) & slope
7. metrics / report / export: Surface metrics, longitudinal profile, HTML report, CAD DXF & CSV
"""

from survey_core.models import (
    CodeConfig,
    ContourLine,
    LocalOrigin,
    RemovedPoint,
    SurveyPoint,
    SurveyState,
)
from survey_core.pipeline import STEP_REGISTRY, run_pipeline_to_step, run_step

__all__ = [
    "STEP_REGISTRY",
    "CodeConfig",
    "ContourLine",
    "LocalOrigin",
    "RemovedPoint",
    "SurveyPoint",
    "SurveyState",
    "run_pipeline_to_step",
    "run_step",
]
