export type AnnotationMode = 'tracking' | 'detection' | 'obb' | 'classification'

export interface Detection {
  bbox: [number, number, number, number]   // [x1, y1, x2, y2]
  confidence: number
  category_id: number
  track_id: number | null
  source: 'model' | 'manual'
  internal_id: number | null
}

export interface OBBDetection {
  cx: number; cy: number
  width: number; height: number
  angle: number
  confidence: number
  category_id: number
  source: 'model' | 'manual'
}

export interface Category {
  id: number
  name: string
  color?: string
}

export interface AnnotationState {
  active: boolean
  mode: AnnotationMode
  frame_index: number
  video_name: string
  total_sources: number
  current_source_index: number
  in_review: boolean
  review_idx: number | null
  total_saved: number
  annotation_mode: boolean
  remove_mode: boolean
  selection_mode: boolean
  pan_mode: boolean
  edit_id_mode: boolean
  zoom_scale: number
  roi_defined: boolean
  roi_points: [number, number][]
  status_message: string
  classes: string[]
  categories: Category[]
  current_detections: Detection[]
  manual_detections: Detection[]
  selected_detection: [string, number] | null
  info: string
  frame_b64: string
  // OBB-only
  current_obb_detections?: OBBDetection[]
  manual_obb_detections?: OBBDetection[]
}

export interface WizardMode {
  value: AnnotationMode
  label: string
}

export interface OutputStateInfo {
  path: string
  annotations_path: string
  label: string
  task_mode: AnnotationMode | null
  class_names: string[]
  image_count: number
  annotation_count: number
  modified_at: string | null
}

export interface StartSessionRequest {
  mode: AnnotationMode
  data_root: string
  weights_paths: string[]
  target_classes: string[]
  output_dir?: string
  annotations_path?: string
  resume_existing_annotations?: boolean
  category_metadata?: object[]
  confidence_threshold?: number
}
