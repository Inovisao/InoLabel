export type TaskMode = "tracking" | "detection" | "obb" | "classification";

export interface SessionStartRequest {
  mode: TaskMode;
  data_root: string;
  output_dir: string;
  classes: string[];
  weights_paths: string[];
  confidence_threshold: number;
  resume_existing: boolean;
}

export interface SessionStatus {
  active: boolean;
  mode?: TaskMode;
  total_frames: number;
  current_index: number;
  classes: string[];
  autosaved: boolean;
}

export interface Annotation {
  id: number;
  image_id: number;
  category_id: number;
  bbox: [number, number, number, number];
  track_id?: number;
  source: string;
}

export interface FrameResponse {
  index: number;
  total: number;
  image_b64: string;
  filename: string;
  annotations: Annotation[];
  is_saved: boolean;
}

export interface ClassItem {
  id: number;
  name: string;
  color?: string;
}
