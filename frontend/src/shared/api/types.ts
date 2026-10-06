export type TaskMode = "tracking" | "detection" | "obb" | "keypoint" | "classification";

/** Modo keypoint: pontos de uma classe, na ordem de clique; esqueleto com índices a partir de 0. */
export interface KeypointClassSpec {
  name: string;
  keypoints: string[];
  skeleton?: [number, number][];
}

/** [x, y, v] — v: 0 ausente, 1 oculto, 2 visível (convenção COCO). */
export type Keypoint = [number, number, number];

export interface SessionStartRequest {
  mode: TaskMode;
  data_root: string;
  output_dir: string;
  classes: string[];
  weights_paths: string[];
  confidence_threshold: number;
  resume_existing: boolean;
  keypoint_classes?: KeypointClassSpec[];
}

export interface SessionStatus {
  active: boolean;
  mode?: TaskMode;
  total_frames: number;
  current_index: number;
  classes: string[];
  autosaved: boolean;
  session_id?: string;
  data_path?: string;
  output_path?: string;
}

export interface ProjectEntry {
  name: string;
  path: string;
  data_path: string;
  mode: string;
  annotated_frames: number;
  classes: string[];
  created_at: string;
  last_modified: string;
}

export interface Annotation {
  id: number;
  image_id: number;
  category_id: number;
  bbox: [number, number, number, number];
  obb?: OBBGeometry | null;
  track_id?: number | null;
  source: string;
  score?: number | null;
  keypoints?: Keypoint[] | null;
}

export interface AnnotationPatch {
  category_id?: number;
  track_id?: number | null;
  bbox?: [number, number, number, number];
  /** Modo OBB: o backend recalcula cantos e bbox a partir de cx, cy, w, h e angle. */
  obb?: OBBGeometry;
  /** Modo keypoint: o backend recalcula a bbox a partir dos pontos. */
  keypoints?: Keypoint[];
}

export interface OBBGeometry {
  cx: number;
  cy: number;
  width: number;
  height: number;
  angle: number;
  angle_unit: "degrees";
  points?: [number, number][] | null;
}

export interface FrameResponse {
  index: number;
  total: number;
  image_b64: string;
  filename: string;
  annotations: Annotation[];
  is_saved: boolean;
  /** Revisada sem objetos (vira negativo na exportação). */
  reviewed?: boolean;
  /** Modo classificação: índice da classe já atribuída à imagem. */
  classification_id?: number | null;
}

export interface ClassItem {
  id: number;
  name: string;
  color?: string;
  /** Modo keypoint: nomes dos pontos na ordem de clique e esqueleto. */
  keypoints?: string[];
  skeleton?: [number, number][];
}

export interface ClassificationResult {
  image_id: number;
  filename: string;
  top1_class_id: number;
  top1_class_name: string;
  top1_confidence?: number | null;
  top_k: Array<Record<string, unknown>>;
  destination_path: string;
  operation: string;
}

export interface ExportProgress {
  export_id: string;
  progress: number;
  current_file: string;
  status: string;
  output_path?: string | null;
  zip_path?: string | null;
}

export interface WorkspaceProjectRef {
  folder: string;
  name: string;
  mode: string;
  created_at: string;
}

export interface WorkspaceInfo {
  path: string;
  name: string;
  version: number;
  created_at: string;
  projects: WorkspaceProjectRef[];
}

export interface WorkspaceRecent {
  path: string;
  name: string;
  opened_at: string;
  exists: boolean;
}

export interface WorkspaceOverview {
  current: WorkspaceInfo | null;
  recent: WorkspaceRecent[];
}

export interface AugmentationOption {
  key: string;
  label: string;
  description: string;
}
