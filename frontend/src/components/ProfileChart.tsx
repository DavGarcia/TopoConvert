import React, { useState } from "react";
import { ProfileData } from "../types/survey";
import { formatNum } from "../utils/format";

interface ProfileChartProps {
  profile: ProfileData | null;
  persianDigits: boolean;
}

export const ProfileChart: React.FC<ProfileChartProps> = ({
  profile,
  persianDigits
}) => {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (!profile || !profile.stations || profile.stations.length < 2) {
    return null;
  }

  const stations = profile.stations;
  const dists = stations.map((s) => s.distance_m);
  const zMeans = stations.map((s) => s.z_mean);
  const zMins = stations.map((s) => s.z_min);
  const zMaxs = stations.map((s) => s.z_max);

  const maxDist = Math.max(...dists, 1);
  const minZ = Math.min(...zMins);
  const maxZ = Math.max(...zMaxs);
  const spanZ = Math.max(maxZ - minZ, 0.2);

  const width = 560;
  const height = 195;
  const padL = 52;
  const padR = 18;
  const padT = 18;
  const padB = 34;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const sx = (d: number) => padL + (d / maxDist) * plotW;
  const sy = (z: number) => padT + plotH - ((z - minZ) / spanZ) * plotH;

  const topBand = stations.map((s) => `${sx(s.distance_m).toFixed(1)},${sy(s.z_max).toFixed(1)}`);
  const botBand = [...stations]
    .reverse()
    .map((s) => `${sx(s.distance_m).toFixed(1)},${sy(s.z_min).toFixed(1)}`);
  const bandPolygon = [...topBand, ...botBand].join(" ");

  const pathD = stations
    .map(
      (s, idx) =>
        `${idx === 0 ? "M" : "L"}${sx(s.distance_m).toFixed(1)},${sy(s.z_mean).toFixed(1)}`
    )
    .join(" ");

  const activeStation = hoverIdx !== null ? stations[hoverIdx] : stations[Math.floor(stations.length / 2)];

  return (
    <div className="profile-chart-card">
      <div className="profile-chart-svg-wrap">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="profile-svg"
          role="img"
          aria-label="نمودار پروفیل طولی"
        >
          <rect x="0" y="0" width={width} height={height} rx="8" fill="rgba(15,23,42,0.75)" />
          {[0, 0.5, 1].map((t, i) => {
            const yVal = padT + t * plotH;
            const zVal = maxZ - t * spanZ;
            return (
              <g key={i}>
                <line
                  x1={padL}
                  y1={yVal}
                  x2={padL + plotW}
                  y2={yVal}
                  stroke="rgba(148,163,184,0.18)"
                  strokeDasharray="3 3"
                />
                <text
                  x={padL - 6}
                  y={yVal + 4}
                  textAnchor="end"
                  fill="#94a3b8"
                  fontSize="10"
                >
                  {formatNum(zVal, 2, persianDigits)}
                </text>
              </g>
            );
          })}

          <polygon points={bandPolygon} fill="rgba(56, 189, 248, 0.18)" />
          <path d={pathD} fill="none" stroke="#38bdf8" strokeWidth="2.3" />

          {stations.map((s, idx) => (
            <circle
              key={idx}
              cx={sx(s.distance_m)}
              cy={sy(s.z_mean)}
              r={hoverIdx === idx ? 4.5 : 2.3}
              fill={hoverIdx === idx ? "#fbbf24" : "#38bdf8"}
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHoverIdx(idx)}
              onClick={() => setHoverIdx(idx)}
            />
          ))}

          <line
            x1={padL}
            y1={padT + plotH}
            x2={padL + plotW}
            y2={padT + plotH}
            stroke="#475569"
          />
          <text x={padL} y={height - 8} textAnchor="start" fill="#94a3b8" fontSize="10">
            {formatNum(0, 0, persianDigits)}m
          </text>
          <text
            x={padL + plotW / 2}
            y={height - 8}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="10"
          >
            {formatNum(maxDist / 2, 1, persianDigits)}m
          </text>
          <text
            x={padL + plotW}
            y={height - 8}
            textAnchor="end"
            fill="#94a3b8"
            fontSize="10"
          >
            {formatNum(maxDist, 1, persianDigits)}m
          </text>
        </svg>
      </div>
      {activeStation && (
        <div className="profile-station-bar">
          <span>
            کیلومتراژ: <strong>{formatNum(activeStation.distance_m, 1, persianDigits)}m</strong>
          </span>
          <span>
            ارتفاع میانگین: <strong>{formatNum(activeStation.z_mean, 3, persianDigits)}m</strong>
          </span>
          <span>
            بازه عرضی: <strong>{formatNum(activeStation.z_min, 2, persianDigits)}</strong> تا{" "}
            <strong>{formatNum(activeStation.z_max, 2, persianDigits)}m</strong>
          </span>
        </div>
      )}
    </div>
  );
};
