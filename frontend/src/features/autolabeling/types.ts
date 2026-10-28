export interface ModelConfig {
  adapter: string;
  model_id?: string | null;
  parameters?: Record<string, unknown>;
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
  score_type?: string;
  prompt?: string | null;
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
  pending_frames?: number[];
  accepted: number;
  error: string | null;
  config: ModelConfig;
  model_definition?: { name: string; id: string } | null;
  outcomes: Record<string, { status: string; count?: number; error?: string }>;
}

export interface Draft {
  bbox: [number, number, number, number];
  category_id: number;
}

export interface InputSchema {
  type?: string;
  title?: string;
  description?: string;
  default?: unknown;
  enum?: (string | number | boolean)[];
  properties?: Record<string, InputSchema>;
  required?: string[];
  items?: InputSchema;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  minItems?: number;
  maxItems?: number;
  $ref?: string;
  $defs?: Record<string, InputSchema>;
  "x-control"?: string;
  "x-step"?: number;
}

export interface CatalogModel {
  id: string;
  name: string;
  adapter: string;
  source: "imported" | "catalog";
  strategy: "trained_model" | "prompt_based";
  description: string;
  tasks: string[];
  schema_version: number;
  requires_checkpoint?: boolean;
  can_prepare?: boolean;
  setup_instructions?: string;
  provider_model?: string;
  download_size_bytes?: number;
  installed?: boolean;
  provider_available?: boolean;
  input_schema: InputSchema;
  availability: "setup_required" | "configured";
  reasons: string[];
  setup: { model_path: string };
  documentation_url: string;
}
