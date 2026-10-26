"""`survey_core/pipeline.py`: Ordered 7-step pipeline registry and execution runner."""

from __future__ import annotations

from typing import Any, Callable, Optional

from survey_core import clean, codes, contour, filt, io, metrics, tin
from survey_core.models import SurveyState

StepFunc = Callable[
    [SurveyState, Optional[dict[str, Any]]],
    tuple[SurveyState, dict[str, Any], dict[str, Any]],
]

STEP_REGISTRY: dict[int, dict[str, Any]] = {
    1: {
        "step": 1,
        "key": "upload",
        "title_fa": "بارگذاری و تشخیص فرمت",
        "runner": io.run,
    },
    2: {
        "step": 2,
        "key": "clean",
        "title_fa": "پاک‌سازی نقاط تکراری و پرت",
        "runner": clean.run,
    },
    3: {
        "step": 3,
        "key": "codes",
        "title_fa": "مدیریت کدها و خطوط شکست",
        "runner": codes.run,
    },
    4: {
        "step": 4,
        "key": "tin",
        "title_fa": "مثلث‌بندی شبکه نامنظم (TIN)",
        "runner": tin.run,
    },
    5: {
        "step": 5,
        "key": "filter",
        "title_fa": "فیلتر اضلاع و مرز محدوده",
        "runner": filt.run,
    },
    6: {
        "step": 6,
        "key": "contour",
        "title_fa": "منحنی‌های میزان و نقشه شیب",
        "runner": contour.run,
    },
    7: {
        "step": 7,
        "key": "report",
        "title_fa": "گزارش مهندسی و خروجی CAD",
        "runner": metrics.run,
    },
}


def run_step(
    state: SurveyState,
    step_num: int,
    params: dict[str, Any] | None = None,
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run step `step_num` (1..7), automatically running any unexecuted prerequisite steps with defaults."""
    if step_num not in STEP_REGISTRY:
        raise ValueError(f"شماره مرحله نامعتبر است: {step_num} (مراحل مجاز ۱ تا ۷)")

    current_state = state
    # Ensure prerequisite steps 1..(step_num-1) have run at least once
    for prereq in range(1, step_num):
        if prereq not in current_state.completed_steps:
            runner: StepFunc = STEP_REGISTRY[prereq]["runner"]
            current_state, _, _ = runner(current_state, {})

    target_runner: StepFunc = STEP_REGISTRY[step_num]["runner"]
    return target_runner(current_state, params or {})


def run_pipeline_to_step(
    raw_text: str,
    filename: str = "survey.txt",
    up_to_step: int = 7,
    step_params: dict[int, dict[str, Any]] | None = None,
) -> tuple[SurveyState, dict[str, Any], dict[str, Any]]:
    """Run the pipeline from Step 1 through `up_to_step` with optional per-step parameters."""
    step_params = step_params or {}
    p1 = dict(step_params.get(1, {}))
    p1["raw_text"] = raw_text
    p1["filename"] = filename

    state = SurveyState(raw_text=raw_text, filename=filename)
    stats: dict[str, Any] = {}
    viewer_payload: dict[str, Any] = {}

    for s in range(1, up_to_step + 1):
        params = p1 if s == 1 else step_params.get(s, {})
        state, stats, viewer_payload = run_step(state, s, params)

    return (state, stats, viewer_payload)
