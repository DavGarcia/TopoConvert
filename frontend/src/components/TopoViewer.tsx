import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import fa from "../i18n/fa.json";
import { LayerVisibility, ViewerPayload, ViewerPoint } from "../types/survey";
import { formatInt, formatNum } from "../utils/format";

interface TopoViewerProps {
  payload: ViewerPayload | null;
  activeStep: number;
  persianDigits: boolean;
  liveMaxEdge: number | null;
  liveMinAngle: number;
  showSlopeHeatmap: boolean;
  layers: LayerVisibility;
  onToggleLayer: (key: keyof LayerVisibility) => void;
}

function elevationColorRGB(t: number): [number, number, number] {
  const c = Math.max(0, Math.min(1, t));
  // Hypsometric engineering ramp: deep teal -> emerald -> amber -> warm coral
  if (c < 0.33) {
    const u = c / 0.33;
    return [
      Math.round(16 + u * 20),
      Math.round(115 + u * 70),
      Math.round(175 - u * 45)
    ];
  }
  if (c < 0.66) {
    const u = (c - 0.33) / 0.33;
    return [
      Math.round(36 + u * 195),
      Math.round(185 - u * 15),
      Math.round(130 - u * 85)
    ];
  }
  const u = (c - 0.66) / 0.34;
  return [
    Math.round(231 + u * 18),
    Math.round(170 - u * 95),
    Math.round(45 - u * 10)
  ];
}

function slopeColorRGB(deg: number): [number, number, number] {
  const c = Math.max(0, Math.min(1, deg / 45.0));
  if (c < 0.5) {
    const u = c * 2.0;
    return [Math.round(34 + u * 210), Math.round(197 - u * 20), Math.round(94 - u * 60)];
  }
  const u = (c - 0.5) * 2.0;
  return [Math.round(244), Math.round(177 - u * 120), Math.round(34 + u * 25)];
}

function pointInTriangle(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number
): boolean {
  const v0x = cx - ax;
  const v0y = cy - ay;
  const v1x = bx - ax;
  const v1y = by - ay;
  const v2x = px - ax;
  const v2y = py - ay;

  const dot00 = v0x * v0x + v0y * v0y;
  const dot01 = v0x * v1x + v0y * v1y;
  const dot02 = v0x * v2x + v0y * v2y;
  const dot11 = v1x * v1x + v1y * v1y;
  const dot12 = v1x * v2x + v1y * v2y;

  const denom = dot00 * dot11 - dot01 * dot01;
  if (Math.abs(denom) < 1e-12) return false;
  const invDenom = 1.0 / denom;
  const u = (dot11 * dot02 - dot01 * dot12) * invDenom;
  const v = (dot00 * dot12 - dot01 * dot02) * invDenom;
  return u >= 0 && v >= 0 && u + v <= 1;
}

export const TopoViewer: React.FC<TopoViewerProps> = ({
  payload,
  activeStep,
  persianDigits,
  liveMaxEdge,
  liveMinAngle,
  showSlopeHeatmap,
  layers,
  onToggleLayer
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvas2dRef = useRef<HTMLCanvasElement | null>(null);
  const mount3dRef = useRef<HTMLDivElement | null>(null);

  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d");
  const [verticalExag, setVerticalExag] = useState<number>(6);
  const [canvasSize, setCanvasSize] = useState<{ w: number; h: number }>({ w: 800, h: 600 });

  // 2D Camera state: world center (cx, cy) and zoom scale (pixels per meter)
  const [cam2d, setCam2d] = useState<{ cx: number; cy: number; scale: number }>({
    cx: 0,
    cy: 0,
    scale: 2
  });

  // 3D Orbit state (works for both Three.js WebGL and Canvas3D fallback)
  const [orbit3d, setOrbit3d] = useState<{ yaw: number; pitch: number; zoom: number }>({
    yaw: 0.65,
    pitch: 0.55,
    zoom: 1.0
  });
  const [webglLost, setWebglLost] = useState<boolean>(false);

  // Inspection & Measurement state
  const [selectedPoint, setSelectedPoint] = useState<ViewerPoint | null>(null);
  const [selectedTri, setSelectedTri] = useState<{
    index: number;
    planArea: number;
    area3d: number;
    slopeDeg: number;
    maxEdge: number;
  } | null>(null);
  const [measureActive, setMeasureActive] = useState<boolean>(false);
  const [measurePts, setMeasurePts] = useState<
    { x: number; y: number; z: number }[]
  >([]);

  // Animated reveal progress (0..1)
  const [revealProgress, setRevealProgress] = useState<number>(1);

  // Fit 2D camera to bounds (accounts for mobile bottom sheet on portrait screens)
  const fitToExtents = useCallback(() => {
    if (!payload) return;
    const b = payload.bounds_local;
    const spanX = Math.max(b.max_x - b.min_x, 2);
    const spanY = Math.max(b.max_y - b.min_y, 2);
    const isPortraitMobile = canvasSize.w < 768 && canvasSize.h > 500;
    const padFactor = isPortraitMobile ? 0.68 : 0.76;
    const w = Math.max(canvasSize.w, 280);
    const effectiveH = isPortraitMobile
      ? Math.max(canvasSize.h * 0.44, 160)
      : Math.max(canvasSize.h - 110, 200);
    const scale = Math.min((w * padFactor) / spanX, (effectiveH * padFactor) / spanY);
    const safeScale = Math.max(scale, 0.05);
    // Shift camera cy downward in world coords so geometry renders higher on portrait mobile
    const mobileYOffsetWorld = isPortraitMobile ? (canvasSize.h * 0.22) / safeScale : 0;
    setCam2d({
      cx: (b.min_x + b.max_x) / 2,
      cy: (b.min_y + b.max_y) / 2 - mobileYOffsetWorld,
      scale: safeScale
    });
  }, [payload, canvasSize.w, canvasSize.h]);

  // Observe container resize & orientation change
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateSize = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 20 && rect.height > 20) {
        setCanvasSize({ w: Math.floor(rect.width), h: Math.floor(rect.height) });
      }
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(el);
    window.addEventListener("orientationchange", updateSize);
    return () => {
      ro.disconnect();
      window.removeEventListener("orientationchange", updateSize);
    };
  }, []);

  // Re-fit when payload bounds change first time
  const prevOriginKey = useRef<string>("");
  useEffect(() => {
    if (!payload) return;
    const key = `${payload.origin.e0.toFixed(2)}_${payload.origin.n0.toFixed(2)}_${canvasSize.w > 300}`;
    if (key !== prevOriginKey.current) {
      prevOriginKey.current = key;
      fitToExtents();
    }
  }, [payload, canvasSize.w, fitToExtents]);

  // Step transition animation (respects prefers-reduced-motion)
  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setRevealProgress(1);
      return;
    }
    setRevealProgress(0.15);
    let frame = 0;
    const start = performance.now();
    const duration = 380;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      setRevealProgress(t);
      if (t < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [activeStep, payload?.tin?.all_triangles?.length]);

  // Compute active triangle indices for live Step 5 slider filtering
  const visibleTriangleIndices = useMemo(() => {
    if (!payload?.tin) return [];
    const tin = payload.tin;
    const total = tin.all_triangles.length;
    const out: number[] = [];
    const limitCount = Math.ceil(total * revealProgress);

    for (let i = 0; i < limitCount; i++) {
      if (activeStep >= 5) {
        const edgeLen = tin.max_edges[i] ?? 0;
        const minAng = tin.min_angles[i] ?? 180;
        const maxAllowed = liveMaxEdge !== null && liveMaxEdge > 0 ? liveMaxEdge : Infinity;
        if (edgeLen > maxAllowed) continue;
        if (liveMinAngle > 0 && minAng < liveMinAngle) continue;
      }
      out.push(i);
    }
    return out;
  }, [payload?.tin, activeStep, liveMaxEdge, liveMinAngle, revealProgress]);

  // Draw 2D Plan View (and 3D software fallback if WebGL context is unavailable/lost)
  useEffect(() => {
    const canvas = canvas2dRef.current;
    if (!canvas || !payload) return;
    if (viewMode === "3d" && !webglLost) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvasSize.w;
    const h = canvasSize.h;
    canvas.width = Math.max(1, Math.floor(w * dpr));
    canvas.height = Math.max(1, Math.floor(h * dpr));

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.save();
    ctx.scale(dpr, dpr);

    // Background fill
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    ctx.fillStyle = isLight ? "#f1f5f9" : "#070d19";
    ctx.fillRect(0, 0, w, h);

    const b = payload.bounds_local;
    const zSpan = Math.max(b.max_z - b.min_z, 0.01);

    if (viewMode === "3d" && webglLost) {
      // 3D Isometric / Orbit projection fallback on Canvas
      const spanXY = Math.max(b.max_x - b.min_x, b.max_y - b.min_y, 10);
      const scale3d = (Math.min(w, h) * 0.68 * orbit3d.zoom) / spanXY;
      const cosY = Math.cos(orbit3d.yaw);
      const sinY = Math.sin(orbit3d.yaw);
      const cosP = Math.cos(orbit3d.pitch);
      const sinP = Math.sin(orbit3d.pitch);
      const cx0 = (b.min_x + b.max_x) / 2;
      const cy0 = (b.min_y + b.max_y) / 2;
      const cz0 = (b.min_z + b.max_z) / 2;

      const proj3d = (x: number, y: number, z: number): [number, number] => {
        const dx = x - cx0;
        const dy = y - cy0;
        const dz = (z - cz0) * verticalExag;
        const rx = dx * cosY - dy * sinY;
        const ry = dx * sinY + dy * cosY;
        const sx = w / 2 + rx * scale3d;
        const sy = h / 2 - (ry * sinP + dz * cosP) * scale3d;
        return [sx, sy];
      };

      if (payload.tin && payload.tin.vertices.length > 0) {
        const verts = payload.tin.vertices;
        const tris = payload.tin.all_triangles;
        for (const ti of visibleTriangleIndices) {
          const t = tris[ti];
          if (!t) continue;
          const v0 = verts[t[0]];
          const v1 = verts[t[1]];
          const v2 = verts[t[2]];
          if (!v0 || !v1 || !v2) continue;
          const [x0, y0] = proj3d(v0[0], v0[1], v0[2]);
          const [x1, y1] = proj3d(v1[0], v1[1], v1[2]);
          const [x2, y2] = proj3d(v2[0], v2[1], v2[2]);
          const zNorm = ((v0[2] + v1[2] + v2[2]) / 3 - b.min_z) / zSpan;
          const [r, g, bl] = showSlopeHeatmap
            ? slopeColorRGB(payload.tin.slopes_deg[ti] ?? 0)
            : elevationColorRGB(zNorm);
          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.closePath();
          if (layers.tinFaces) {
            ctx.fillStyle = `rgba(${r},${g},${bl},0.65)`;
            ctx.fill();
          }
          if (layers.tinEdges) {
            ctx.strokeStyle = "rgba(148,163,184,0.38)";
            ctx.lineWidth = 0.65;
            ctx.stroke();
          }
        }
      }
      if (layers.points) {
        for (const p of payload.points) {
          const [px, py] = proj3d(p.x, p.y, p.z);
          ctx.fillStyle = p.color || "#38bdf8";
          ctx.beginPath();
          ctx.arc(px, py, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.restore();
      return;
    }

    // 2D World -> Screen coordinate transform
    const toScreenX = (wx: number) => w / 2 + (wx - cam2d.cx) * cam2d.scale;
    const toScreenY = (wy: number) => h / 2 - (wy - cam2d.cy) * cam2d.scale;

    // 1. Subtle engineering grid
    const rawStep = 80 / Math.max(cam2d.scale, 1e-4);
    const mag = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const residual = rawStep / mag;
    const gridStep = residual > 5 ? 10 * mag : residual > 2 ? 5 * mag : residual > 1 ? 2 * mag : mag;

    const worldLeft = cam2d.cx - w / (2 * cam2d.scale);
    const worldRight = cam2d.cx + w / (2 * cam2d.scale);
    const worldBottom = cam2d.cy - h / (2 * cam2d.scale);
    const worldTop = cam2d.cy + h / (2 * cam2d.scale);

    ctx.strokeStyle = isLight ? "rgba(15,23,42,0.07)" : "rgba(148,163,184,0.08)";
    ctx.lineWidth = 1;
    const startX = Math.floor(worldLeft / gridStep) * gridStep;
    for (let gx = startX; gx <= worldRight; gx += gridStep) {
      const sx = toScreenX(gx);
      ctx.beginPath();
      ctx.moveTo(sx, 0);
      ctx.lineTo(sx, h);
      ctx.stroke();
    }
    const startY = Math.floor(worldBottom / gridStep) * gridStep;
    for (let gy = startY; gy <= worldTop; gy += gridStep) {
      const sy = toScreenY(gy);
      ctx.beginPath();
      ctx.moveTo(0, sy);
      ctx.lineTo(w, sy);
      ctx.stroke();
    }

    // 2. TIN Triangles (Step >= 4)
    if (
      activeStep >= 4 &&
      payload.tin &&
      payload.tin.vertices.length > 0 &&
      (layers.tinFaces || layers.tinEdges)
    ) {
      const verts = payload.tin.vertices;
      const tris = payload.tin.all_triangles;

      for (const ti of visibleTriangleIndices) {
        const t = tris[ti];
        if (!t) continue;
        const v0 = verts[t[0]];
        const v1 = verts[t[1]];
        const v2 = verts[t[2]];
        if (!v0 || !v1 || !v2) continue;

        const sx0 = toScreenX(v0[0]);
        const sy0 = toScreenY(v0[1]);
        const sx1 = toScreenX(v1[0]);
        const sy1 = toScreenY(v1[1]);
        const sx2 = toScreenX(v2[0]);
        const sy2 = toScreenY(v2[1]);

        ctx.beginPath();
        ctx.moveTo(sx0, sy0);
        ctx.lineTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
        ctx.closePath();

        if (layers.tinFaces) {
          const zAvg = (v0[2] + v1[2] + v2[2]) / 3;
          const zNorm = (zAvg - b.min_z) / zSpan;
          const [r, g, bl] = showSlopeHeatmap
            ? slopeColorRGB(payload.tin.slopes_deg[ti] ?? 0)
            : elevationColorRGB(zNorm);
          ctx.fillStyle =
            selectedTri?.index === ti
              ? "rgba(251, 191, 36, 0.65)"
              : `rgba(${r}, ${g}, ${bl}, 0.42)`;
          ctx.fill();
        }
        if (layers.tinEdges) {
          ctx.strokeStyle =
            selectedTri?.index === ti
              ? "#fbbf24"
              : isLight
                ? "rgba(51,65,85,0.35)"
                : "rgba(148,163,184,0.32)";
          ctx.lineWidth = selectedTri?.index === ti ? 1.8 : 0.65;
          ctx.stroke();
        }
      }
    }

    // 3. Boundary Polygon
    if (layers.boundary && payload.boundary && payload.boundary.length >= 3) {
      ctx.beginPath();
      payload.boundary.forEach(([bx, by], idx) => {
        const sx = toScreenX(bx);
        const sy = toScreenY(by);
        if (idx === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      });
      ctx.strokeStyle = "#3b82f6";
      ctx.lineWidth = 2.0;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 4. Breaklines
    if (layers.breaklines && payload.breaklines && payload.breaklines.length > 0) {
      for (const bl of payload.breaklines) {
        if (bl.coords.length < 2) continue;
        ctx.beginPath();
        bl.coords.forEach(([bx, by], idx) => {
          const sx = toScreenX(bx);
          const sy = toScreenY(by);
          if (idx === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        });
        ctx.strokeStyle = bl.color || "#f59e0b";
        ctx.lineWidth = 2.4;
        ctx.stroke();
      }
    }

    // 5. Contours (Step >= 6)
    if (activeStep >= 6 && layers.contours && payload.contours.length > 0) {
      for (const c of payload.contours) {
        if (c.points.length < 2) continue;
        ctx.beginPath();
        c.points.forEach(([px, py], idx) => {
          const sx = toScreenX(px);
          const sy = toScreenY(py);
          if (idx === 0) ctx.moveTo(sx, sy);
          else ctx.lineTo(sx, sy);
        });
        ctx.strokeStyle = c.is_major
          ? "#fbbf24"
          : isLight
            ? "rgba(15,23,42,0.55)"
            : "rgba(226,232,240,0.62)";
        ctx.lineWidth = c.is_major ? 1.7 : 0.85;
        ctx.stroke();

        if (c.label && (c.is_major || cam2d.scale > 4)) {
          const lx = toScreenX(c.label.x);
          const ly = toScreenY(c.label.y);
          ctx.save();
          ctx.translate(lx, ly);
          ctx.font = "600 10px Vazirmatn, sans-serif";
          ctx.fillStyle = c.is_major ? "#fde68a" : "#cbd5e1";
          ctx.textAlign = "center";
          ctx.fillText(
            formatNum(c.elevation, 1, persianDigits),
            0,
            -3
          );
          ctx.restore();
        }
      }
    }

    // 6. Removed points (Step >= 2)
    if (activeStep >= 2 && layers.removed && payload.removed_points.length > 0) {
      for (const rp of payload.removed_points) {
        const sx = toScreenX(rp.x);
        const sy = toScreenY(rp.y);
        ctx.strokeStyle = rp.reason === "outlier" ? "#f43f5e" : "#f59e0b";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, sy, 5.5, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(sx - 4, sy - 4);
        ctx.lineTo(sx + 4, sy + 4);
        ctx.moveTo(sx + 4, sy - 4);
        ctx.lineTo(sx - 4, sy + 4);
        ctx.stroke();
      }
    }

    // 7. Survey points (fast flat rendering when > 3000 points, rich rendering otherwise)
    if (layers.points) {
      if (
        payload.points_flat &&
        payload.points_flat.length > 9000 &&
        payload.points.length < payload.points_flat.length / 3
      ) {
        const flat = payload.points_flat;
        for (let i = 0; i < flat.length; i += 3) {
          const sx = toScreenX(flat[i]);
          const sy = toScreenY(flat[i + 1]);
          if (sx < 0 || sx > w || sy < 0 || sy > h) continue;
          const zNorm = (flat[i + 2] - b.min_z) / zSpan;
          const [r, g, bl] = elevationColorRGB(zNorm);
          ctx.fillStyle = `rgb(${r},${g},${bl})`;
          ctx.fillRect(sx - 1, sy - 1, 2.2, 2.2);
        }
      } else {
        for (const p of payload.points) {
          const sx = toScreenX(p.x);
          const sy = toScreenY(p.y);
          if (sx < -20 || sx > w + 20 || sy < -20 || sy > h + 20) continue;

          const zNorm = (p.z - b.min_z) / zSpan;
          const [r, g, bl] = elevationColorRGB(zNorm);
          const isSelected = selectedPoint?.index === p.index;

          ctx.beginPath();
          ctx.arc(sx, sy, isSelected ? 5.5 : 3.0, 0, Math.PI * 2);
          ctx.fillStyle = activeStep === 3 ? p.color : `rgb(${r},${g},${bl})`;
          ctx.fill();
          if (isSelected) {
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 2;
            ctx.stroke();
          }

          if (layers.pointIds || (layers.elevations && cam2d.scale > 3.5)) {
            ctx.font = "500 10px Vazirmatn, sans-serif";
            ctx.textAlign = "left";
            if (layers.pointIds) {
              ctx.fillStyle = isLight ? "#0f172a" : "#e2e8f0";
              ctx.fillText(formatInt(Number(p.id) || p.index + 1, persianDigits), sx + 5, sy - 2);
            }
            if (layers.elevations) {
              ctx.fillStyle = "#38bdf8";
              ctx.fillText(formatNum(p.elev, 2, persianDigits), sx + 5, sy + 10);
            }
          }
        }
      }
    }

    // 8. Distance Measure Overlay
    if (measurePts.length > 0) {
      ctx.strokeStyle = "#f43f5e";
      ctx.fillStyle = "#f43f5e";
      ctx.lineWidth = 2.2;
      const p0 = measurePts[0];
      const sx0 = toScreenX(p0.x);
      const sy0 = toScreenY(p0.y);
      ctx.beginPath();
      ctx.arc(sx0, sy0, 4.5, 0, Math.PI * 2);
      ctx.fill();

      if (measurePts.length === 2) {
        const p1 = measurePts[1];
        const sx1 = toScreenX(p1.x);
        const sy1 = toScreenY(p1.y);
        ctx.beginPath();
        ctx.moveTo(sx0, sy0);
        ctx.lineTo(sx1, sy1);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(sx1, sy1, 4.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.restore();
  }, [
    payload,
    activeStep,
    viewMode,
    webglLost,
    canvasSize,
    cam2d,
    orbit3d,
    verticalExag,
    layers,
    visibleTriangleIndices,
    selectedPoint,
    selectedTri,
    measurePts,
    showSlopeHeatmap,
    persianDigits
  ]);

  // Three.js 3D WebGL View
  useEffect(() => {
    if (viewMode !== "3d" || !payload || !mount3dRef.current) return;
    const mount = mount3dRef.current;
    mount.innerHTML = "";

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    } catch {
      setWebglLost(true);
      return;
    }

    const w = Math.max(canvasSize.w, 280);
    const h = Math.max(canvasSize.h, 240);
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    mount.appendChild(renderer.domElement);

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setWebglLost(true);
    };
    const handleContextRestored = () => {
      setWebglLost(false);
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost);
    renderer.domElement.addEventListener("webglcontextrestored", handleContextRestored);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070d19);

    const b = payload.bounds_local;
    const spanX = Math.max(b.max_x - b.min_x, 10);
    const spanY = Math.max(b.max_y - b.min_y, 10);
    const maxSpan = Math.max(spanX, spanY);
    const zSpan = Math.max(b.max_z - b.min_z, 0.01);
    const cx0 = (b.min_x + b.max_x) / 2;
    const cy0 = (b.min_y + b.max_y) / 2;
    const cz0 = (b.min_z + b.max_z) / 2;

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, maxSpan * 15);
    const radius = (maxSpan * 1.15) / Math.max(orbit3d.zoom, 0.2);
    camera.position.set(
      radius * Math.cos(orbit3d.pitch) * Math.sin(orbit3d.yaw),
      radius * Math.sin(orbit3d.pitch),
      radius * Math.cos(orbit3d.pitch) * Math.cos(orbit3d.yaw)
    );
    camera.lookAt(0, 0, 0);

    const ambient = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambient);
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.75);
    dirLight.position.set(maxSpan, maxSpan * 1.5, maxSpan);
    scene.add(dirLight);

    // 1. TIN Mesh
    if (payload.tin && payload.tin.vertices.length > 0 && visibleTriangleIndices.length > 0) {
      const verts = payload.tin.vertices;
      const tris = payload.tin.all_triangles;
      const positions = new Float32Array(visibleTriangleIndices.length * 9);
      const colors = new Float32Array(visibleTriangleIndices.length * 9);

      visibleTriangleIndices.forEach((ti, outIdx) => {
        const t = tris[ti];
        if (!t) return;
        const v0 = verts[t[0]];
        const v1 = verts[t[1]];
        const v2 = verts[t[2]];
        if (!v0 || !v1 || !v2) return;

        const pts = [v0, v1, v2];
        pts.forEach((v, k) => {
          const base = outIdx * 9 + k * 3;
          positions[base] = v[0] - cx0;
          positions[base + 1] = (v[2] - cz0) * verticalExag;
          positions[base + 2] = -(v[1] - cy0);

          const zNorm = (v[2] - b.min_z) / zSpan;
          const [r, g, bl] = showSlopeHeatmap
            ? slopeColorRGB(payload.tin?.slopes_deg[ti] ?? 0)
            : elevationColorRGB(zNorm);
          colors[base] = r / 255;
          colors[base + 1] = g / 255;
          colors[base + 2] = bl / 255;
        });
      });

      const geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      geom.computeVertexNormals();

      if (layers.tinFaces) {
        const mat = new THREE.MeshLambertMaterial({
          vertexColors: true,
          side: THREE.DoubleSide
        });
        scene.add(new THREE.Mesh(geom, mat));
      }
      if (layers.tinEdges) {
        const wireMat = new THREE.MeshBasicMaterial({
          color: 0x94a3b8,
          wireframe: true,
          transparent: true,
          opacity: 0.32
        });
        scene.add(new THREE.Mesh(geom, wireMat));
      }
    }

    // 2. Draped 3D Contours
    if (activeStep >= 6 && layers.contours && payload.contours.length > 0) {
      for (const c of payload.contours) {
        if (c.points.length < 2) continue;
        const linePts = c.points.map(
          ([px, py]) =>
            new THREE.Vector3(
              px - cx0,
              (c.z - cz0) * verticalExag + 0.08,
              -(py - cy0)
            )
        );
        const lGeom = new THREE.BufferGeometry().setFromPoints(linePts);
        const lMat = new THREE.LineBasicMaterial({
          color: c.is_major ? 0xfbbf24 : 0xe2e8f0
        });
        scene.add(new THREE.Line(lGeom, lMat));
      }
    }

    // 3. 3D Survey Points
    if (layers.points && payload.points.length > 0) {
      const pPos = new Float32Array(payload.points.length * 3);
      payload.points.forEach((p, idx) => {
        pPos[idx * 3] = p.x - cx0;
        pPos[idx * 3 + 1] = (p.z - cz0) * verticalExag + 0.12;
        pPos[idx * 3 + 2] = -(p.y - cy0);
      });
      const pGeom = new THREE.BufferGeometry();
      pGeom.setAttribute("position", new THREE.BufferAttribute(pPos, 3));
      const pMat = new THREE.PointsMaterial({ color: 0x38bdf8, size: 4, sizeAttenuation: false });
      scene.add(new THREE.Points(pGeom, pMat));
    }

    renderer.render(scene, camera);

    return () => {
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      renderer.domElement.removeEventListener("webglcontextrestored", handleContextRestored);
      renderer.dispose();
    };
  }, [
    viewMode,
    payload,
    activeStep,
    canvasSize,
    orbit3d,
    verticalExag,
    layers,
    visibleTriangleIndices,
    showSlopeHeatmap
  ]);

  // Pointer & touch gestures (pan, pinch-zoom, orbit, tap inspection)
  const dragRef = useRef<{
    active: boolean;
    moved: boolean;
    startX: number;
    startY: number;
    camCx: number;
    camCy: number;
    yaw: number;
    pitch: number;
  }>({
    active: false,
    moved: false,
    startX: 0,
    startY: 0,
    camCx: 0,
    camCy: 0,
    yaw: 0,
    pitch: 0
  });

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    dragRef.current = {
      active: true,
      moved: false,
      startX: e.clientX,
      startY: e.clientY,
      camCx: cam2d.cx,
      camCy: cam2d.cy,
      yaw: orbit3d.yaw,
      pitch: orbit3d.pitch
    };
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current.active) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    if (Math.hypot(dx, dy) > 4) {
      dragRef.current.moved = true;
    }
    if (viewMode === "2d") {
      setCam2d((prev) => ({
        ...prev,
        cx: dragRef.current.camCx - dx / prev.scale,
        cy: dragRef.current.camCy + dy / prev.scale
      }));
    } else {
      setOrbit3d((prev) => ({
        ...prev,
        yaw: dragRef.current.yaw - dx * 0.008,
        pitch: Math.max(0.1, Math.min(1.45, dragRef.current.pitch + dy * 0.008))
      }));
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    const wasMoved = dragRef.current.moved;
    dragRef.current.active = false;
    if (wasMoved || viewMode !== "2d" || !payload) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const wx = cam2d.cx + (sx - canvasSize.w / 2) / cam2d.scale;
    const wy = cam2d.cy - (sy - canvasSize.h / 2) / cam2d.scale;

    // Find nearest point within 14px
    let bestPt: ViewerPoint | null = null;
    let bestDistPx = 14;
    for (const p of payload.points) {
      const px = canvasSize.w / 2 + (p.x - cam2d.cx) * cam2d.scale;
      const py = canvasSize.h / 2 - (p.y - cam2d.cy) * cam2d.scale;
      const d = Math.hypot(px - sx, py - sy);
      if (d < bestDistPx) {
        bestDistPx = d;
        bestPt = p;
      }
    }

    if (measureActive) {
      const zVal = bestPt ? bestPt.z : payload.bounds_local.min_z;
      const xVal = bestPt ? bestPt.x : wx;
      const yVal = bestPt ? bestPt.y : wy;
      setMeasurePts((prev) => (prev.length >= 2 ? [{ x: xVal, y: yVal, z: zVal }] : [...prev, { x: xVal, y: yVal, z: zVal }]));
      return;
    }

    if (bestPt) {
      setSelectedPoint(bestPt);
      setSelectedTri(null);
      return;
    }

    // Check triangle hit in Step >= 4
    if (activeStep >= 4 && payload.tin && payload.tin.vertices.length > 0) {
      const verts = payload.tin.vertices;
      const tris = payload.tin.all_triangles;
      for (const ti of visibleTriangleIndices) {
        const t = tris[ti];
        if (!t) continue;
        const v0 = verts[t[0]];
        const v1 = verts[t[1]];
        const v2 = verts[t[2]];
        if (
          v0 &&
          v1 &&
          v2 &&
          pointInTriangle(wx, wy, v0[0], v0[1], v1[0], v1[1], v2[0], v2[1])
        ) {
          setSelectedTri({
            index: ti,
            planArea: payload.tin.plan_areas[ti] ?? 0,
            area3d: payload.tin.areas_3d[ti] ?? 0,
            slopeDeg: payload.tin.slopes_deg[ti] ?? 0,
            maxEdge: payload.tin.max_edges[ti] ?? 0
          });
          setSelectedPoint(null);
          return;
        }
      }
    }

    setSelectedPoint(null);
    setSelectedTri(null);
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const factor = e.deltaY < 0 ? 1.18 : 0.85;
    if (viewMode === "2d") {
      setCam2d((prev) => ({
        ...prev,
        scale: Math.max(0.05, Math.min(200, prev.scale * factor))
      }));
    } else {
      setOrbit3d((prev) => ({
        ...prev,
        zoom: Math.max(0.25, Math.min(8, prev.zoom * factor))
      }));
    }
  };

  // Scale bar length computation
  const scaleBar = useMemo(() => {
    const targetPx = 90;
    const meters = targetPx / Math.max(cam2d.scale, 1e-4);
    const mag = Math.pow(10, Math.floor(Math.log10(meters)));
    const res = meters / mag;
    const niceM = res >= 5 ? 5 * mag : res >= 2 ? 2 * mag : mag;
    const barPx = Math.max(36, Math.min(140, niceM * cam2d.scale));
    return { meters: niceM, px: barPx };
  }, [cam2d.scale]);

  // Distance measurement summary
  const measureSummary = useMemo(() => {
    if (measurePts.length < 2) return null;
    const [a, b] = measurePts;
    const d2d = Math.hypot(b.x - a.x, b.y - a.y);
    const dz = b.z - a.z;
    const d3d = Math.hypot(d2d, dz);
    const slopePct = d2d > 1e-6 ? (Math.abs(dz) / d2d) * 100 : 0;
    return { d2d, dz, d3d, slopePct };
  }, [measurePts]);

  const layerKeys: (keyof LayerVisibility)[] = [
    "points",
    "pointIds",
    "elevations",
    "tinFaces",
    "tinEdges",
    "contours",
    "breaklines",
    "boundary",
    "removed"
  ];

  return (
    <div
      ref={containerRef}
      className="topo-viewer-root"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onDoubleClick={fitToExtents}
      onWheel={handleWheel}
    >
      {/* 2D Canvas */}
      <canvas
        ref={canvas2dRef}
        className="topo-canvas-2d"
        style={{
          display: viewMode === "2d" || webglLost ? "block" : "none"
        }}
      />

      {/* 3D WebGL Mount */}
      <div
        ref={mount3dRef}
        className="topo-mount-3d"
        style={{
          display: viewMode === "3d" && !webglLost ? "block" : "none"
        }}
      />

      {/* Top Floating Controls Stack: Row 1 (2D/3D Switch + Tools), Row 2 (Layer Chips) */}
      <div
        className="viewer-top-stack"
        onPointerDown={(e) => e.stopPropagation()}
      >
        <div className="viewer-top-toolbar">
          <div className="segmented-2d-3d" role="group" aria-label="تغییر نمای دوبعدی و سه‌بعدی">
            <button
              type="button"
              className={`seg-btn ${viewMode === "2d" ? "active" : ""}`}
              onClick={() => setViewMode("2d")}
            >
              {fa.viewer.mode2d}
            </button>
            <button
              type="button"
              className={`seg-btn ${viewMode === "3d" ? "active" : ""}`}
              onClick={() => setViewMode("3d")}
            >
              {fa.viewer.mode3d}
            </button>
          </div>

          <div className="viewer-tool-btns">
            <button
              type="button"
              className="viewer-icon-btn"
              title={fa.viewer.fitView}
              aria-label={fa.viewer.fitView}
              onClick={fitToExtents}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
              </svg>
            </button>
            <button
              type="button"
              className="viewer-icon-btn"
              title={fa.viewer.zoomIn}
              aria-label={fa.viewer.zoomIn}
              onClick={() =>
                viewMode === "2d"
                  ? setCam2d((p) => ({ ...p, scale: Math.min(200, p.scale * 1.3) }))
                  : setOrbit3d((p) => ({ ...p, zoom: Math.min(8, p.zoom * 1.25) }))
              }
            >
              +
            </button>
            <button
              type="button"
              className="viewer-icon-btn"
              title={fa.viewer.zoomOut}
              aria-label={fa.viewer.zoomOut}
              onClick={() =>
                viewMode === "2d"
                  ? setCam2d((p) => ({ ...p, scale: Math.max(0.05, p.scale * 0.75) }))
                  : setOrbit3d((p) => ({ ...p, zoom: Math.max(0.25, p.zoom * 0.8) }))
              }
            >
              −
            </button>
            {viewMode === "2d" && (
              <button
                type="button"
                className={`viewer-icon-btn ${measureActive ? "active" : ""}`}
                title={fa.viewer.measureTool}
                aria-label={fa.viewer.measureTool}
                onClick={() => {
                  setMeasureActive((v) => !v);
                  setMeasurePts([]);
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M3 17l14-14 4 4-14 14-4-4zM14 6l2 2M10 10l2 2M6 14l2 2" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Layer Toggles Strip */}
        <div
          className="viewer-layers-bar"
          role="toolbar"
          aria-label={fa.viewer.layersTitle}
        >
          {layerKeys.map((k) => (
            <button
              key={k}
              type="button"
              className={`layer-chip ${layers[k] ? "active" : ""}`}
              onClick={() => onToggleLayer(k)}
            >
              {fa.viewer.layers[k]}
            </button>
          ))}
        </div>

        {/* 3D Vertical Exaggeration Slider */}
        {viewMode === "3d" && (
          <div className="viewer-3d-exag-bar">
            <label htmlFor="vexag-slider">
              {fa.viewer.verticalExag}{" "}
              <strong>{formatInt(verticalExag, persianDigits)}×</strong>
            </label>
            <input
              id="vexag-slider"
              type="range"
              min={1}
              max={20}
              step={1}
              value={verticalExag}
              onChange={(e) => setVerticalExag(Number(e.target.value))}
            />
          </div>
        )}
      </div>

      {/* North Arrow & Scale Bar & Legend */}
      { payload && (
        <div
          className="viewer-hud-bottom"
          onPointerDown={(e) => e.stopPropagation()}
        >
          <div className="hud-compass-scale">
            <div className="north-badge" title={fa.viewer.north}>
              <span className="north-arrow-icon">▲</span>
              <span>N</span>
            </div>
            {viewMode === "2d" && (
              <div className="scale-bar-box">
                <div className="scale-bar-line" style={{ width: `${scaleBar.px}px` }} />
                <span>
                  {formatNum(
                    scaleBar.meters,
                    scaleBar.meters < 1 ? 2 : 0,
                    persianDigits
                  )}{" "}
                  متر
                </span>
              </div>
            )}
          </div>

          <div className="hud-legend">
            <div className="legend-title">
              {showSlopeHeatmap ? fa.viewer.legendSlope : fa.viewer.legendElevation}
            </div>
            <div className="legend-gradient-bar" />
            <div className="legend-Ends">
              <span>
                {showSlopeHeatmap
                  ? `${formatInt(0, persianDigits)}°`
                  : `${formatNum(payload.bounds_local.min_elev, 2, persianDigits)}m`}
              </span>
              <span>
                {showSlopeHeatmap
                  ? `${formatInt(45, persianDigits)}°`
                  : `${formatNum(payload.bounds_local.max_elev, 2, persianDigits)}m`}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Inspection Popover (Point / Triangle / Distance Measure) */}
      {(selectedPoint || selectedTri || measureSummary) && (
        <div
          className="viewer-inspect-card"
          onPointerDown={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="inspect-close-btn"
            aria-label="بستن"
            onClick={() => {
              setSelectedPoint(null);
              setSelectedTri(null);
              setMeasurePts([]);
            }}
          >
            ×
          </button>

          {selectedPoint && (
            <div>
              <div className="inspect-title">{fa.viewer.inspectPoint}</div>
              <div className="inspect-grid">
                <span>شماره: <strong>{formatInt(Number(selectedPoint.id) || selectedPoint.index + 1, persianDigits)}</strong></span>
                <span>کد: <strong>{selectedPoint.code}</strong></span>
                <span>E: <strong>{formatNum(selectedPoint.e, 3, persianDigits)}</strong></span>
                <span>N: <strong>{formatNum(selectedPoint.n, 3, persianDigits)}</strong></span>
                <span>Z: <strong>{formatNum(selectedPoint.elev, 3, persianDigits)}m</strong></span>
              </div>
            </div>
          )}

          {selectedTri && (
            <div>
              <div className="inspect-title">{fa.viewer.inspectTriangle}</div>
              <div className="inspect-grid">
                <span>مساحت افقی: <strong>{formatNum(selectedTri.planArea, 2, persianDigits)} m²</strong></span>
                <span>مساحت ۳بعدی: <strong>{formatNum(selectedTri.area3d, 2, persianDigits)} m²</strong></span>
                <span>شیب: <strong>{formatNum(selectedTri.slopeDeg, 1, persianDigits)}°</strong></span>
                <span>بلندترین ضلع: <strong>{formatNum(selectedTri.maxEdge, 2, persianDigits)}m</strong></span>
              </div>
            </div>
          )}

          {measureSummary && (
            <div>
              <div className="inspect-title">{fa.viewer.measureTool}</div>
              <div className="inspect-grid">
                <span>فاصله افقی: <strong>{formatNum(measureSummary.d2d, 2, persianDigits)}m</strong></span>
                <span>اختلاف تراز (ΔZ): <strong>{formatNum(measureSummary.dz, 3, persianDigits)}m</strong></span>
                <span>فاصله مایل ۳D: <strong>{formatNum(measureSummary.d3d, 2, persianDigits)}m</strong></span>
                <span>شیب خط: <strong>{formatNum(measureSummary.slopePct, 1, persianDigits)}٪</strong></span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
