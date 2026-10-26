import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ProfileChart } from "./components/ProfileChart";
import { TopoViewer } from "./components/TopoViewer";
import fa from "./i18n/fa.json";
import {
  CodeConfigItem,
  LayerVisibility,
  SessionResponse
} from "./types/survey";
import { formatInt, formatNum, toPersianDigits } from "./utils/format";

const TOTAL_STEPS = 7;

export const App: React.FC = () => {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [activeStep, setActiveStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Global UI preferences
  const [persianDigits, setPersianDigits] = useState<boolean>(true);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [autoAdvance, setAutoAdvance] = useState<boolean>(false);
  const [sidePanelOpen, setSidePanelOpen] = useState<boolean>(true);
  const [sheetState, setSheetState] = useState<"collapsed" | "half" | "full">("half");

  // Viewer layer toggles
  const [layers, setLayers] = useState<LayerVisibility>({
    points: true,
    pointIds: false,
    elevations: false,
    tinEdges: true,
    tinFaces: true,
    contours: true,
    breaklines: true,
    boundary: true,
    removed: true
  });

  // Step 1 params
  const [crsInput, setCrsInput] = useState<string>("EPSG:32640");
  const [swapNe, setSwapNe] = useState<boolean>(false);

  // Step 2 params
  const [dupTolerance, setDupTolerance] = useState<number>(0.001);
  const [outlierZ, setOutlierZ] = useState<number>(4.0);

  // Step 3 params
  const [codeRoles, setCodeRoles] = useState<Record<string, string>>({});
  const [codeColors, setCodeColors] = useState<Record<string, string>>({});

  // Step 4 params
  const [honorBreaklines, setHonorBreaklines] = useState<boolean>(true);
  const [densifyBreaklines, setDensifyBreaklines] = useState<boolean>(false);

  // Step 5 params (also drives live client-side triangle filtering!)
  const [maxEdgeLength, setMaxEdgeLength] = useState<number>(10.0);
  const [minAngleDeg, setMinAngleDeg] = useState<number>(0.0);
  const [useBoundaryPoly, setUseBoundaryPoly] = useState<boolean>(true);

  // Step 6 params
  const [contourInterval, setContourInterval] = useState<number>(0.2);
  const [majorMultiplier, setMajorMultiplier] = useState<number>(5);
  const [showContourLabels, setShowContourLabels] = useState<boolean>(true);
  const [showSlopeHeatmap, setShowSlopeHeatmap] = useState<boolean>(false);

  // Step 7 params
  const [refElevation, setRefElevation] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  const syncStateFromResponse = useCallback((data: SessionResponse) => {
    setSession(data);
    setActiveStep(data.active_step);
    const s1 = data.step_stats?.["1"];
    if (s1?.crs?.code) {
      setCrsInput(s1.crs.code);
    }
    if (s1?.detected_format) {
      setSwapNe(Boolean(s1.detected_format.ne_swap_applied));
    }
    if (data.viewer_payload?.codes) {
      const rolesMap: Record<string, string> = {};
      const colorsMap: Record<string, string> = {};
      data.viewer_payload.codes.forEach((c: CodeConfigItem) => {
        rolesMap[c.code] = c.role;
        colorsMap[c.code] = c.color;
      });
      setCodeRoles(rolesMap);
      setCodeColors(colorsMap);
    }
    if (data.viewer_payload?.bounds_local) {
      const minElev = data.viewer_payload.bounds_local.min_elev;
      setRefElevation((prev) => (prev === "" ? minElev.toFixed(3) : prev));
    }
  }, []);

  const handleLoadDemo = useCallback(async (initialStep = 1) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ up_to_step: initialStep })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "خطا در بارگذاری نمونه" }));
        throw new Error(err.detail || "خطا در بارگذاری نمونه");
      }
      const data: SessionResponse = await res.json();
      syncStateFromResponse(data);
    } catch (err: any) {
      setErrorMsg(err.message || "خطا در ارتباط با سرور");
    } finally {
      setLoading(false);
    }
  }, [syncStateFromResponse]);

  // Support URL query ?demo=1&step=N for automated inspection and quick start
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "1") {
      const targetStep = Math.max(1, Math.min(7, Number(params.get("step") || "1")));
      handleLoadDemo(targetStep);
    }
  }, [handleLoadDemo]);

  const handleFileUpload = async (file: File) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("crs", crsInput);
      const res = await fetch("/api/sessions", {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "خطا در بارگذاری فایل" }));
        throw new Error(err.detail || "خطا در بارگذاری فایل");
      }
      const data: SessionResponse = await res.json();
      syncStateFromResponse(data);
    } catch (err: any) {
      setErrorMsg(err.message || "خطا در بارگذاری فایل");
    } finally {
      setLoading(false);
    }
  };

  const buildStepParams = useCallback(
    (stepNum: number): Record<string, any> => {
      switch (stepNum) {
        case 1:
          return {
            crs: crsInput,
            crs_confirmed: crsInput !== "EPSG:32640",
            swap_ne: swapNe
          };
        case 2:
          return {
            duplicate_tolerance: dupTolerance,
            outlier_z_threshold: outlierZ
          };
        case 3:
          return {
            code_roles: codeRoles,
            code_colors: codeColors
          };
        case 4:
          return {
            honor_breaklines: honorBreaklines,
            densify_breaklines: densifyBreaklines
          };
        case 5:
          return {
            max_edge_length: maxEdgeLength,
            min_angle_deg: minAngleDeg,
            use_boundary_polygon: useBoundaryPoly
          };
        case 6:
          return {
            interval: contourInterval,
            major_multiplier: majorMultiplier,
            add_labels: showContourLabels,
            compute_slope_heatmap: true
          };
        case 7:
          return {
            reference_elevation: refElevation ? Number(refElevation) : undefined
          };
        default:
          return {};
      }
    },
    [
      crsInput,
      swapNe,
      dupTolerance,
      outlierZ,
      codeRoles,
      codeColors,
      honorBreaklines,
      densifyBreaklines,
      maxEdgeLength,
      minAngleDeg,
      useBoundaryPoly,
      contourInterval,
      majorMultiplier,
      showContourLabels,
      refElevation
    ]
  );

  const runStepOnServer = useCallback(
    async (stepNum: number, customParams?: Record<string, any>) => {
      if (!session) return null;
      setLoading(true);
      setErrorMsg(null);
      try {
        const params = customParams ?? buildStepParams(stepNum);
        const res = await fetch(
          `/api/sessions/${session.session_id}/steps/${stepNum}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ params })
          }
        );
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "خطا در اجرای مرحله" }));
          throw new Error(err.detail || "خطا در اجرای مرحله");
        }
        const data: SessionResponse = await res.json();
        syncStateFromResponse(data);
        return data;
      } catch (err: any) {
        setErrorMsg(err.message || "خطا در اجرای مرحله");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [session, buildStepParams, syncStateFromResponse]
  );

  const handlePrimaryContinue = async () => {
    if (!session) {
      await handleLoadDemo(1);
      return;
    }
    // Run current step with current controls, then advance to next step and run it
    const currentOk = await runStepOnServer(activeStep);
    if (!currentOk) return;
    if (activeStep < TOTAL_STEPS) {
      const nextStep = activeStep + 1;
      await runStepOnServer(nextStep);
    }
  };

  const handleJumpToStep = async (targetStep: number) => {
    if (!session) {
      if (targetStep === 1) return;
      await handleLoadDemo(targetStep);
      return;
    }
    if (session.completed_steps.includes(targetStep)) {
      setActiveStep(targetStep);
      return;
    }
    await runStepOnServer(targetStep);
  };

  const handleToggleLayer = (key: keyof LayerVisibility) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Live filtered area calculation in Step 5 as slider moves
  const liveFilterStats = useMemo(() => {
    const tin = session?.viewer_payload?.tin;
    if (!tin || !tin.all_triangles || tin.all_triangles.length === 0) {
      return null;
    }
    let activeCount = 0;
    let planArea = 0;
    let area3d = 0;
    let totalPlan = 0;
    let total3d = 0;

    for (let i = 0; i < tin.all_triangles.length; i++) {
      const pa = tin.plan_areas[i] ?? 0;
      const a3 = tin.areas_3d[i] ?? 0;
      totalPlan += pa;
      total3d += a3;

      const edge = tin.max_edges[i] ?? 0;
      const ang = tin.min_angles[i] ?? 180;
      if (
        (maxEdgeLength <= 0 || edge <= maxEdgeLength) &&
        (minAngleDeg <= 0 || ang >= minAngleDeg)
      ) {
        activeCount++;
        planArea += pa;
        area3d += a3;
      }
    }

    return {
      totalCount: tin.all_triangles.length,
      activeCount,
      removedCount: tin.all_triangles.length - activeCount,
      planArea,
      area3d,
      totalPlan,
      total3d
    };
  }, [session?.viewer_payload?.tin, maxEdgeLength, minAngleDeg]);

  // Bottom sheet touch drag handler on mobile
  const sheetDragRef = useRef<{ startY: number; active: boolean }>({
    startY: 0,
    active: false
  });

  const handleSheetTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    sheetDragRef.current = { startY: e.touches[0].clientY, active: true };
  };

  const handleSheetTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    if (!sheetDragRef.current.active) return;
    sheetDragRef.current.active = false;
    const dy = e.changedTouches[0].clientY - sheetDragRef.current.startY;
    if (dy < -40) {
      setSheetState((prev) => (prev === "collapsed" ? "half" : "full"));
    } else if (dy > 40) {
      setSheetState((prev) => (prev === "full" ? "half" : "collapsed"));
    }
  };

  const s1Stats = session?.step_stats?.["1"];
  const s2Stats = session?.step_stats?.["2"];
  const s4Stats = session?.step_stats?.["4"];
  const s5Stats = session?.step_stats?.["5"];
  const s6Stats = session?.step_stats?.["6"];
  const s7Stats = session?.step_stats?.["7"];

  const stepMeta = (fa.steps as Record<string, { short: string; title: string; desc: string }>)[
    String(activeStep)
  ];

  return (
    <div className="app-shell" dir="rtl" lang="fa">
      {/* Top Engineering Header */}
      <header className="top-header">
        <div className="brand-block">
          <div className="brand-logo" aria-hidden="true">
            ▲
          </div>
          <div>
            <div className="brand-title">{fa.appTitle}</div>
            <div className="brand-subtitle">{fa.appSubtitle}</div>
          </div>
        </div>

        {/* Compact Mobile Step Indicator (visible < 768px) */}
        <div className="mobile-step-badge" aria-live="polite">
          <span>
            مرحله {toPersianDigits(activeStep, persianDigits)} از{" "}
            {toPersianDigits(TOTAL_STEPS, persianDigits)}:
          </span>{" "}
          <strong>{stepMeta?.short}</strong>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className="hdr-btn demo-hdr-btn"
            onClick={() => handleLoadDemo(1)}
            disabled={loading}
          >
            {fa.header.loadDemo}
          </button>
          <button
            type="button"
            className="hdr-btn"
            onClick={() => setPersianDigits((v) => !v)}
            aria-pressed={persianDigits}
          >
            {persianDigits ? "۱۲۳" : "123"}
          </button>
          <button
            type="button"
            className="hdr-btn"
            onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
            aria-label={theme === "dark" ? fa.header.themeLight : fa.header.themeDark}
          >
            {theme === "dark" ? "روشن" : "تاریک"}
          </button>
          <button
            type="button"
            className="hdr-btn desktop-only-btn"
            onClick={() => setSidePanelOpen((v) => !v)}
          >
            {fa.header.togglePanel}
          </button>
        </div>
      </header>

      {/* 7-Step Stepper Bar */}
      <nav className="wizard-stepper" aria-label="مراحل پردازش توپوگرافی">
        {[1, 2, 3, 4, 5, 6, 7].map((num) => {
          const info = (fa.steps as Record<string, { short: string; title: string }>)[
            String(num)
          ];
          const isCompleted = session?.completed_steps?.includes(num) ?? false;
          const isCurrent = activeStep === num;
          return (
            <button
              key={num}
              type="button"
              className={`step-pill ${isCurrent ? "current" : ""} ${
                isCompleted ? "completed" : ""
              }`}
              onClick={() => handleJumpToStep(num)}
              disabled={loading}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="step-num">
                {toPersianDigits(num, persianDigits)}
              </span>
              <span className="step-label">{info.short}</span>
            </button>
          );
        })}
      </nav>

      {/* Main Workspace: Side Panel (Right in RTL on Desktop, Bottom Sheet on Mobile) + Viewer */}
      <main className="workspace-grid">
        {/* Controls & Stats Panel */}
        <aside
          className={`wizard-panel sheet-${sheetState} ${
            sidePanelOpen ? "panel-open" : "panel-collapsed"
          }`}
          aria-label="پنل تنظیمات و آمار مرحله"
        >
          {/* Mobile Bottom Sheet Handle & State Switcher */}
          <div
            className="mobile-sheet-header"
            onTouchStart={handleSheetTouchStart}
            onTouchEnd={handleSheetTouchEnd}
          >
            <div className="sheet-grab-bar" />
            <div className="sheet-state-btns">
              <button
                type="button"
                className={`sheet-tab-btn ${sheetState === "collapsed" ? "active" : ""}`}
                onClick={() => setSheetState("collapsed")}
              >
                {fa.actions.sheetCollapsed}
              </button>
              <button
                type="button"
                className={`sheet-tab-btn ${sheetState === "half" ? "active" : ""}`}
                onClick={() => setSheetState("half")}
              >
                {fa.actions.sheetHalf}
              </button>
              <button
                type="button"
                className={`sheet-tab-btn ${sheetState === "full" ? "active" : ""}`}
                onClick={() => setSheetState("full")}
              >
                {fa.actions.sheetFull}
              </button>
            </div>
          </div>

          <div className="panel-scroll-body">
            <div className="step-header-box">
              <h2>{stepMeta?.title}</h2>
              <p>{stepMeta?.desc}</p>
            </div>

            {errorMsg && (
              <div className="alert-banner error-banner" role="alert">
                {errorMsg}
              </div>
            )}

            {/* STEP 1: UPLOAD & PARSE SUMMARY */}
            {activeStep === 1 && (
              <div className="step-section">
                {s1Stats && (
                  <div className="stats-glass-card">
                    <div className="stats-card-title">
                      خلاصه فایل: <strong>{session?.filename}</strong>
                    </div>
                    <div className="stats-kv-grid">
                      <div className="kv-item">
                        <span>{fa.step1.pointCount}</span>
                        <strong>{formatInt(s1Stats.point_count, persianDigits)}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step1.delimiterLabel}</span>
                        <strong>{s1Stats.detected_format?.delimiter_name}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step1.eastingRange}</span>
                        <strong>
                          {formatNum(s1Stats.extents?.easting_min, 3, persianDigits)} تا{" "}
                          {formatNum(s1Stats.extents?.easting_max, 3, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step1.northingRange}</span>
                        <strong>
                          {formatNum(s1Stats.extents?.northing_min, 3, persianDigits)} تا{" "}
                          {formatNum(s1Stats.extents?.northing_max, 3, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step1.elevationRange}</span>
                        <strong>
                          {formatNum(s1Stats.extents?.z_min, 3, persianDigits)} تا{" "}
                          {formatNum(s1Stats.extents?.z_max, 3, persianDigits)} متر
                        </strong>
                      </div>
                    </div>

                    <div className="codes-badges-row">
                      {Object.entries(s1Stats.codes || {}).map(([code, cnt]) => (
                        <span key={code} className="code-pill-badge">
                          کد <strong>{code}</strong>: {formatInt(Number(cnt), persianDigits)} نقطه
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="control-card">
                  <label className="field-label" htmlFor="crs-select">
                    {fa.step1.crsLabel}
                  </label>
                  <select
                    id="crs-select"
                    className="form-select"
                    value={crsInput}
                    onChange={(e) => setCrsInput(e.target.value)}
                  >
                    <option value="EPSG:32640">EPSG:32640 — WGS 84 / UTM Zone 40N (پیش‌فرض)</option>
                    <option value="EPSG:32639">EPSG:32639 — WGS 84 / UTM Zone 39N</option>
                    <option value="EPSG:32638">EPSG:32638 — WGS 84 / UTM Zone 38N</option>
                    <option value="EPSG:32641">EPSG:32641 — WGS 84 / UTM Zone 41N</option>
                  </select>
                  <div className="assumption-note">
                    {fa.step1.crsAssumedWarning}
                  </div>

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={swapNe}
                      onChange={(e) => {
                        setSwapNe(e.target.checked);
                        if (session) {
                          runStepOnServer(1, {
                            crs: crsInput,
                            swap_ne: e.target.checked
                          });
                        }
                      }}
                    />
                    <span>{fa.step1.swapNeLabel}</span>
                  </label>
                </div>

                <div
                  className="upload-dropzone"
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      fileInputRef.current?.click();
                    }
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const f = e.dataTransfer.files?.[0];
                    if (f) handleFileUpload(f);
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.csv,.dat,.xyz"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleFileUpload(f);
                    }}
                  />
                  <div className="dropzone-icon">▲</div>
                  <div className="dropzone-title">{fa.step1.dropzoneTitle}</div>
                  <div className="dropzone-hint">{fa.step1.dropzoneHint}</div>
                </div>

                <button
                  type="button"
                  className="btn-secondary-accent full-width-btn"
                  onClick={() => handleLoadDemo(1)}
                  disabled={loading}
                >
                  {fa.actions.loadDemoPrimary}
                </button>
              </div>
            )}

            {/* STEP 2: CLEAN DUPLICATES & OUTLIERS */}
            {activeStep === 2 && (
              <div className="step-section">
                <div className="control-card">
                  <label className="field-label" htmlFor="dup-tol-slider">
                    {fa.step2.dupToleranceLabel}{" "}
                    <strong>{formatNum(dupTolerance, 3, persianDigits)} m</strong>
                  </label>
                  <input
                    id="dup-tol-slider"
                    type="range"
                    min={0}
                    max={0.25}
                    step={0.001}
                    value={dupTolerance}
                    onChange={(e) => setDupTolerance(Number(e.target.value))}
                  />

                  <label className="field-label" htmlFor="outlier-z-slider">
                    {fa.step2.outlierZLabel}{" "}
                    <strong>{formatNum(outlierZ, 1, persianDigits)}</strong>
                  </label>
                  <input
                    id="outlier-z-slider"
                    type="range"
                    min={2.0}
                    max={8.0}
                    step={0.1}
                    value={outlierZ}
                    onChange={(e) => setOutlierZ(Number(e.target.value))}
                  />

                  <button
                    type="button"
                    className="btn-secondary-accent full-width-btn"
                    onClick={() => runStepOnServer(2)}
                    disabled={loading}
                  >
                    {fa.actions.rerun}
                  </button>
                </div>

                {s2Stats && (
                  <div className="stats-glass-card">
                    <div className="stats-kv-grid">
                      <div className="kv-item">
                        <span>{fa.step2.beforeCount}</span>
                        <strong>{formatInt(s2Stats.before_count, persianDigits)}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step2.afterCount}</span>
                        <strong className="text-emerald">
                          {formatInt(s2Stats.after_count, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step2.dupRemoved}</span>
                        <strong className="text-amber">
                          {formatInt(s2Stats.duplicates_removed, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step2.outlierRemoved}</span>
                        <strong className="text-rose">
                          {formatInt(s2Stats.outliers_removed, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step2.minNnDist}</span>
                        <strong>
                          {formatNum(s2Stats.min_nearest_neighbor_m, 4, persianDigits)} متر
                        </strong>
                      </div>
                    </div>

                    {s2Stats.removed_points?.length > 0 ? (
                      <div className="table-scroll-box">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>شماره</th>
                              <th>کد</th>
                              <th>علت حذف</th>
                              <th>توضیح</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s2Stats.removed_points.map((rp: any) => (
                              <tr key={rp.index}>
                                <td>{formatInt(Number(rp.id) || rp.index + 1, persianDigits)}</td>
                                <td>{rp.code}</td>
                                <td>
                                  <span className={`reason-tag ${rp.reason}`}>
                                    {rp.reason === "outlier" ? "پرت ارتفاعی" : "تکراری"}
                                  </span>
                                </td>
                                <td>{toPersianDigits(rp.detail, persianDigits)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="ok-note">✓ {fa.step2.noRemoved}</div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* STEP 3: CODES & BREAKLINES */}
            {activeStep === 3 && (
              <div className="step-section">
                <div className="assumption-note">
                  {fa.step3.neverGuessBanner}
                </div>

                <div className="control-card">
                  <div className="table-scroll-box">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>{fa.step3.codeCol}</th>
                          <th>{fa.step3.countCol}</th>
                          <th>{fa.step3.colorCol}</th>
                          <th>{fa.step3.roleCol}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(session?.viewer_payload?.codes || []).map((c) => (
                          <tr key={c.code}>
                            <td>
                              <strong>{c.code}</strong>
                            </td>
                            <td>{formatInt(c.count, persianDigits)}</td>
                            <td>
                              <input
                                type="color"
                                className="color-picker-input"
                                aria-label={`رنگ کد ${c.code}`}
                                value={codeColors[c.code] || c.color}
                                onChange={(e) =>
                                  setCodeColors((prev) => ({
                                    ...prev,
                                    [c.code]: e.target.value
                                  }))
                                }
                              />
                            </td>
                            <td>
                              <select
                                className="form-select compact-select"
                                aria-label={`نقش کد ${c.code}`}
                                value={codeRoles[c.code] || c.role}
                                onChange={(e) =>
                                  setCodeRoles((prev) => ({
                                    ...prev,
                                    [c.code]: e.target.value
                                  }))
                                }
                              >
                                <option value="point">{fa.step3.roles.point}</option>
                                <option value="breakline">{fa.step3.roles.breakline}</option>
                                <option value="boundary">{fa.step3.roles.boundary}</option>
                                <option value="ignore">{fa.step3.roles.ignore}</option>
                              </select>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <button
                    type="button"
                    className="btn-secondary-accent full-width-btn"
                    onClick={() => runStepOnServer(3)}
                    disabled={loading}
                  >
                    {fa.actions.rerun}
                  </button>
                </div>
              </div>
            )}

            {/* STEP 4: TIN TRIANGULATION */}
            {activeStep === 4 && (
              <div className="step-section">
                <div className="control-card">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={honorBreaklines}
                      onChange={(e) => setHonorBreaklines(e.target.checked)}
                    />
                    <span>{fa.step4.honorBreaklines}</span>
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={densifyBreaklines}
                      onChange={(e) => setDensifyBreaklines(e.target.checked)}
                    />
                    <span>{fa.step4.densifyBreaklines}</span>
                  </label>

                  <button
                    type="button"
                    className="btn-secondary-accent full-width-btn"
                    onClick={() => runStepOnServer(4)}
                    disabled={loading}
                  >
                    {fa.actions.rerun}
                  </button>
                </div>

                {s4Stats && (
                  <div className="stats-glass-card">
                    <div className="stats-kv-grid">
                      <div className="kv-item">
                        <span>{fa.step4.vertexCount}</span>
                        <strong>{formatInt(s4Stats.vertex_count, persianDigits)}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step4.triangleCount}</span>
                        <strong>{formatInt(s4Stats.triangle_count, persianDigits)}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step4.edgeCount}</span>
                        <strong>{formatInt(s4Stats.edge_count, persianDigits)}</strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step4.unfilteredPlanArea}</span>
                        <strong>
                          {formatNum(s4Stats.unfiltered_plan_area_m2, 2, persianDigits)} m²
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step4.unfiltered3dArea}</span>
                        <strong>
                          {formatNum(s4Stats.unfiltered_surface_area_3d_m2, 2, persianDigits)} m²
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step4.medianMaxEdge}</span>
                        <strong>
                          {formatNum(s4Stats.edge_length_stats_m?.median, 2, persianDigits)} متر
                        </strong>
                      </div>
                    </div>
                    <div className="method-note-box">
                      {toPersianDigits(s4Stats.method_note || "", persianDigits)}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* STEP 5: LIVE EDGE FILTER & BOUNDARY */}
            {activeStep === 5 && (
              <div className="step-section">
                <div className="control-card">
                  <label className="field-label" htmlFor="max-edge-slider">
                    {fa.step5.maxEdgeSlider}{" "}
                    <strong>{formatNum(maxEdgeLength, 1, persianDigits)} متر</strong>
                  </label>
                  <input
                    id="max-edge-slider"
                    type="range"
                    min={2.0}
                    max={60.0}
                    step={0.5}
                    value={maxEdgeLength}
                    onChange={(e) => setMaxEdgeLength(Number(e.target.value))}
                  />

                  <label className="field-label" htmlFor="min-angle-slider">
                    {fa.step5.minAngleSlider}{" "}
                    <strong>{formatNum(minAngleDeg, 1, persianDigits)}°</strong>
                  </label>
                  <input
                    id="min-angle-slider"
                    type="range"
                    min={0.0}
                    max={25.0}
                    step={0.5}
                    value={minAngleDeg}
                    onChange={(e) => setMinAngleDeg(Number(e.target.value))}
                  />

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={useBoundaryPoly}
                      onChange={(e) => setUseBoundaryPoly(e.target.checked)}
                    />
                    <span>{fa.step5.useBoundary}</span>
                  </label>

                  <button
                    type="button"
                    className="btn-secondary-accent full-width-btn"
                    onClick={() => runStepOnServer(5)}
                    disabled={loading}
                  >
                    {fa.actions.rerun}
                  </button>
                </div>

                <div className="stats-glass-card">
                  <div className="stats-kv-grid">
                    <div className="kv-item highlight-kv">
                      <span>{fa.step5.livePlanArea}</span>
                      <strong className="text-emerald">
                        {formatNum(
                          liveFilterStats?.planArea ?? s5Stats?.filtered_plan_area_m2,
                          2,
                          persianDigits
                        )}{" "}
                        m²
                      </strong>
                    </div>
                    <div className="kv-item highlight-kv">
                      <span>{fa.step5.live3dArea}</span>
                      <strong className="text-sky">
                        {formatNum(
                          liveFilterStats?.area3d ?? s5Stats?.filtered_surface_area_3d_m2,
                          2,
                          persianDigits
                        )}{" "}
                        m²
                      </strong>
                    </div>
                    <div className="kv-item">
                      <span>{fa.step5.activeTris}</span>
                      <strong>
                        {formatInt(
                          liveFilterStats?.activeCount ?? s5Stats?.active_triangles_after,
                          persianDigits
                        )}
                      </strong>
                    </div>
                    <div className="kv-item">
                      <span>{fa.step5.removedTris}</span>
                      <strong className="text-amber">
                        {formatInt(
                          liveFilterStats?.removedCount ?? s5Stats?.removed_triangles_total,
                          persianDigits
                        )}
                      </strong>
                    </div>
                  </div>
                  <div className="assumption-note">{fa.step5.stripWarning}</div>
                </div>
              </div>
            )}

            {/* STEP 6: CONTOURS & SLOPE HEATMAP */}
            {activeStep === 6 && (
              <div className="step-section">
                <div className="control-card">
                  <label className="field-label" htmlFor="contour-int-slider">
                    {fa.step6.intervalSlider}{" "}
                    <strong>{formatNum(contourInterval, 2, persianDigits)} متر</strong>
                  </label>
                  <input
                    id="contour-int-slider"
                    type="range"
                    min={0.05}
                    max={1.0}
                    step={0.05}
                    value={contourInterval}
                    onChange={(e) => setContourInterval(Number(e.target.value))}
                  />

                  <label className="field-label" htmlFor="major-mult-select">
                    {fa.step6.majorMultLabel}
                  </label>
                  <select
                    id="major-mult-select"
                    className="form-select"
                    value={majorMultiplier}
                    onChange={(e) => setMajorMultiplier(Number(e.target.value))}
                  >
                    <option value={4}>هر ۴ منحنی فرعی (۴×)</option>
                    <option value={5}>هر ۵ منحنی فرعی (۵× استاندارد)</option>
                    <option value={10}>هر ۱۰ منحنی فرعی (۱۰×)</option>
                  </select>

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={showContourLabels}
                      onChange={(e) => setShowContourLabels(e.target.checked)}
                    />
                    <span>{fa.step6.showLabels}</span>
                  </label>

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={showSlopeHeatmap}
                      onChange={(e) => setShowSlopeHeatmap(e.target.checked)}
                    />
                    <span>{fa.step6.showSlopeHeatmap}</span>
                  </label>

                  <button
                    type="button"
                    className="btn-secondary-accent full-width-btn"
                    onClick={() => runStepOnServer(6)}
                    disabled={loading}
                  >
                    {fa.actions.rerun}
                  </button>
                </div>

                {s6Stats && (
                  <div className="stats-glass-card">
                    <div className="stats-kv-grid">
                      <div className="kv-item">
                        <span>{fa.step6.totalContours}</span>
                        <strong>
                          {formatInt(s6Stats.total_contour_polylines, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step6.majorContours}</span>
                        <strong className="text-amber">
                          {formatInt(s6Stats.major_contour_count, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step6.minorContours}</span>
                        <strong>
                          {formatInt(s6Stats.minor_contour_count, persianDigits)}
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step6.meanSlope}</span>
                        <strong>
                          {formatNum(s6Stats.slope_summary?.mean_deg, 2, persianDigits)}° (
                          {formatNum(s6Stats.slope_summary?.mean_pct, 1, persianDigits)}٪)
                        </strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* STEP 7: FINAL METRICS, PROFILE CHART & CAD EXPORTS */}
            {activeStep === 7 && (
              <div className="step-section">
                {session && (
                  <div className="export-actions-card">
                    <div className="field-label">{fa.step7.exportsTitle}</div>
                    <div className="export-btns-grid">
                      <a
                        className="btn-export-primary"
                        href={`/api/sessions/${session.session_id}/export/dxf`}
                        download="topoconvert_survey.dxf"
                      >
                        {fa.actions.downloadDxf}
                      </a>
                      <a
                        className="btn-export-secondary"
                        href={`/api/sessions/${session.session_id}/export/csv`}
                        download="topoconvert_cleaned.csv"
                      >
                        {fa.actions.downloadCsv}
                      </a>
                      <a
                        className="btn-export-secondary"
                        href={`/api/sessions/${session.session_id}/export/report`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {fa.actions.openReport}
                      </a>
                    </div>
                  </div>
                )}

                {s7Stats && (
                  <div className="stats-glass-card">
                    <div className="stats-kv-grid">
                      <div className="kv-item highlight-kv">
                        <span>{fa.step7.planArea}</span>
                        <strong className="text-emerald">
                          {formatNum(s7Stats.planimetric_area_m2, 2, persianDigits)} m²
                        </strong>
                      </div>
                      <div className="kv-item highlight-kv">
                        <span>{fa.step7.surfArea3d}</span>
                        <strong className="text-sky">
                          {formatNum(s7Stats.surface_area_3d_m2, 2, persianDigits)} m²
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step7.unfiltPlanArea}</span>
                        <strong>
                          {formatNum(s7Stats.unfiltered_planimetric_area_m2, 2, persianDigits)} m²
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step7.prismVolume}</span>
                        <strong>
                          {formatNum(s7Stats.prism_volume_net_m3, 2, persianDigits)} m³
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step7.pathLength}</span>
                        <strong>
                          {formatNum(s7Stats.path_length_m, 1, persianDigits)} متر
                        </strong>
                      </div>
                      <div className="kv-item">
                        <span>{fa.step7.zStats}</span>
                        <strong>
                          {formatNum(s7Stats.elevation_m?.min, 2, persianDigits)} /{" "}
                          {formatNum(s7Stats.elevation_m?.mean, 2, persianDigits)} /{" "}
                          {formatNum(s7Stats.elevation_m?.max, 2, persianDigits)}m
                        </strong>
                      </div>
                    </div>
                  </div>
                )}

                <div className="control-card">
                  <div className="field-label">{fa.step7.profileTitle}</div>
                  <ProfileChart
                    profile={session?.viewer_payload?.profile ?? null}
                    persianDigits={persianDigits}
                  />
                </div>

                {s7Stats?.strip_geometry_explanation && (
                  <div className="assumption-note">
                    {toPersianDigits(s7Stats.strip_geometry_explanation, persianDigits)}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sticky Bottom Action Bar (within thumb reach on mobile & desktop) */}
          <div className="panel-sticky-footer">
            <div className="auto-advance-row">
              <label className="checkbox-row compact">
                <input
                  type="checkbox"
                  checked={autoAdvance}
                  onChange={(e) => setAutoAdvance(e.target.checked)}
                />
                <span>{fa.header.autoAdvance}</span>
              </label>
            </div>
            <div className="footer-nav-btns">
              {activeStep > 1 && (
                <button
                  type="button"
                  className="btn-back"
                  onClick={() => setActiveStep((s) => Math.max(1, s - 1))}
                  disabled={loading}
                >
                  {fa.actions.back}
                </button>
              )}
              {activeStep < TOTAL_STEPS ? (
                <button
                  type="button"
                  className="btn-continue-primary"
                  onClick={handlePrimaryContinue}
                  disabled={loading}
                >
                  {loading ? "در حال پردازش..." : fa.actions.continue}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-continue-primary"
                  onClick={() => runStepOnServer(7)}
                  disabled={loading}
                >
                  {loading ? "در حال بروزرسانی..." : fa.actions.rerun}
                </button>
              )}
            </div>
          </div>
        </aside>

        {/* Interactive 2D/3D Viewer */}
        <section className="viewer-stage" aria-label="نمایشگر تعاملی نقشه دوبعدی و سه‌بعدی">
          <TopoViewer
            payload={session?.viewer_payload ?? null}
            activeStep={activeStep}
            persianDigits={persianDigits}
            liveMaxEdge={activeStep >= 5 ? maxEdgeLength : null}
            liveMinAngle={activeStep >= 5 ? minAngleDeg : 0}
            showSlopeHeatmap={showSlopeHeatmap}
            layers={layers}
            onToggleLayer={handleToggleLayer}
          />
        </section>
      </main>
    </div>
  );
};
