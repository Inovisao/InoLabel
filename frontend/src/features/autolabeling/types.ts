export interface ModelConfig {
  adapter: "ultralytics";
  model_path: string;
  confidence: number;
  class_mapping: Record<string, string | null>;
}

export interface Proposal {
  id: string;
  frame_index: number;
  category_id: number;
  class_name: string;
  bbox: [number, number, number, number];
  score: number | null;
  status: "pending" | "accepted" | "rejected";
  annotation_id: number | null;
}

export interface LabelingRun {
  id: string;
  created_at: string;
  status: "queued" | "running" | "succeeded" | "partially_failed" | "failed" | "cancelled" | "interrupted";
  total: number;
  processed: number;
  failed: number;
  pending: number;
  accepted: number;
  error: string | null;
  config: ModelConfig;
  outcomes: Record<string, { status: string; count?: number; error?: string }>;
}

export interface Draft {
  bbox: [number, number, number, number];
  category_id: number;
}
