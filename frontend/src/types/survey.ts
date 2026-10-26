export interface ViewerPoint {
  id: string;
  index: number;
  code: string;
  x: number;
  y: number;
  z: number;
  e: number;
  n: number;
  elev: number;
  color: string;
}

export interface RemovedPointItem {
  id: string;
  index: number;
  code: string;
  easting: number;
  northing: number;
  elevation: number;
  x: number;
  y: number;
  z: number;
  reason: "duplicate" | "outlier";
  metric_value: number;
  detail: string;
}

export interface CodeConfigItem {
  code: string;
  count: number;
  role: "point" | "breakline" | "boundary" | "ignore";
  color: string;
}

export interface BreaklineItem {
  code: string;
  color: string;
  point_ids: string[];
  vertex_indices: number[];
  coords: [number, number, number][];
}

export interface ContourItem {
  elevation: number;
  z: number;
  is_major: boolean;
  points: [number, number][];
  label: {
    x: number;
    y: number;
    angle: number;
    text: string;
  } | null;
}

export interface TinPayload {
  vertices: [number, number, number][];
  vertex_ids: string[];
  vertex_codes: string[];
  all_triangles: [number, number, number][];
  active_triangles: [number, number, number][];
  triangle_mask: boolean[];
  max_edges: number[];
  min_angles: number[];
  plan_areas: number[];
  areas_3d: number[];
  slopes_deg: number[];
  method: string;
  method_note: string;
  decimated_for_viewer?: boolean;
}

export interface ProfileStation {
  x_local: number;
  y_local: number;
  easting: number;
  northing: number;
  z_mean: number;
  z_min: number;
  z_max: number;
  point_count: number;
  distance_m: number;
}

export interface ProfileData {
  stations: ProfileStation[];
  path_length_m: number;
  straight_span_m: number;
  centerline_local: [number, number, number][];
}

export interface ViewerPayload {
  active_step: number;
  origin: { e0: number; n0: number; z0: number };
  crs: string;
  crs_name: string;
  crs_is_assumed: boolean;
  bounds_local: {
    min_x: number;
    max_x: number;
    min_y: number;
    max_y: number;
    min_z: number;
    max_z: number;
    min_elev: number;
    max_elev: number;
  };
  points: ViewerPoint[];
  points_flat?: number[];
  total_point_count?: number;
  removed_points: RemovedPointItem[];
  codes: CodeConfigItem[];
  breaklines: BreaklineItem[];
  boundary: [number, number][] | null;
  holes: [number, number][][];
  tin: TinPayload | null;
  contours: ContourItem[];
  slope_grid: {
    enabled: boolean;
    triangle_slopes_deg: number[];
    triangle_slopes_pct: number[];
    summary: {
      min_deg: number;
      mean_deg: number;
      max_deg: number;
      min_pct: number;
      mean_pct: number;
      max_pct: number;
    };
  } | null;
  profile: ProfileData | null;
}

export interface SessionResponse {
  session_id: string;
  step?: number;
  filename: string;
  active_step: number;
  completed_steps: number[];
  stats: Record<string, any>;
  step_stats: Record<string, Record<string, any>>;
  viewer_payload: ViewerPayload;
}

export interface LayerVisibility {
  points: boolean;
  pointIds: boolean;
  elevations: boolean;
  tinEdges: boolean;
  tinFaces: boolean;
  contours: boolean;
  breaklines: boolean;
  boundary: boolean;
  removed: boolean;
}
