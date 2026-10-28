import { create } from "zustand";
import { schemaDefaults } from "./model-config/schema.ts";
import type { CatalogModel, Draft, LabelingRun, ModelConfig, Proposal } from "./types";

export const emptyConfig = (): ModelConfig => ({ adapter: "ultralytics", model_path: "", confidence: 0.4, class_mapping: {} });

export interface BatchReviewState {
  runId: string;
  frameIndices: number[];
  position: number;
}

interface AutolabelingState {
  catalog: CatalogModel[];
  configDrafts: Record<string, ModelConfig>;
  chooseModel: (model: CatalogModel) => void;
  scope: string;
  indices: string;
  config: ModelConfig;
  configurationLoaded: boolean;
  modelClasses: string[];
  inspectedPath: string;
  sessionId: string | null;
  runId: string | null;
  runs: LabelingRun[];
  proposals: Proposal[];
  drafts: Record<string, Draft>;
  selectedId: string | null;
  batchReview: BatchReviewState | null;
  visible: boolean;
  onlyCurrent: boolean;
  offset: number;
  total: number;
  error: string | null;
  reset: (sessionId: string | null) => void;
  selectRun: (id: string) => void;
  startBatchReview: (runId: string, frameIndices: number[]) => void;
  moveBatchReview: (position: number) => void;
  endBatchReview: () => void;
  edit: (proposal: Proposal, patch: Partial<Draft>) => void;
}

export const useAutolabelingStore = create<AutolabelingState>((set) => ({
  catalog: [], configDrafts: {},
  scope: "current", indices: "", config: emptyConfig(), configurationLoaded: false, modelClasses: [], inspectedPath: "",
  sessionId: null, runId: null, runs: [], proposals: [], drafts: {}, selectedId: null, batchReview: null, visible: true, onlyCurrent: true, offset: 0, total: 0, error: null,
  reset: (sessionId) => set({ sessionId, catalog: [], configDrafts: {}, scope: "current", indices: "", config: emptyConfig(), configurationLoaded: false, modelClasses: [], inspectedPath: "", offset: 0, total: 0, onlyCurrent: true, runId: null, runs: [], proposals: [], drafts: {}, selectedId: null, batchReview: null, error: null }),
  chooseModel: (model) => set((s) => {
    const previous = s.config.model_id ?? s.config.adapter;
    const configDrafts = { ...s.configDrafts, [previous]: s.config };
    const config = configDrafts[model.id] ?? { adapter: model.adapter, model_id: model.id,
      model_path: "", confidence: 0.4, class_mapping: {}, parameters: schemaDefaults(model.input_schema) };
    return { config, configDrafts, configurationLoaded: true, inspectedPath: "", modelClasses: [] };
  }),
  selectRun: (runId) => set({ runId, offset: 0, total: 0, proposals: [], drafts: {}, selectedId: null, batchReview: null }),
  startBatchReview: (runId, frameIndices) => set({ runId, batchReview: { runId, frameIndices, position: 0 }, onlyCurrent: true, offset: 0, total: 0, proposals: [], drafts: {}, selectedId: null }),
  moveBatchReview: (position) => set((s) => s.batchReview ? { batchReview: { ...s.batchReview, position }, offset: 0, total: 0, proposals: [] } : {}),
  endBatchReview: () => set({ batchReview: null }),
  edit: (proposal, patch) => set((state) => ({
    drafts: { ...state.drafts, [proposal.id]: { ...(state.drafts[proposal.id] ?? { bbox: proposal.bbox, category_id: proposal.category_id }), ...patch } },
    selectedId: proposal.id,
  })),
}));
