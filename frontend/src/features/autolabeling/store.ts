import { create } from "zustand";
import type { Draft, LabelingRun, ModelConfig, Proposal } from "./types";

export const emptyConfig = (): ModelConfig => ({ adapter: "ultralytics", model_path: "", confidence: 0.4, class_mapping: {} });

interface AutolabelingState {
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
  visible: boolean;
  onlyCurrent: boolean;
  offset: number;
  total: number;
  error: string | null;
  reset: (sessionId: string | null) => void;
  selectRun: (id: string) => void;
  edit: (proposal: Proposal, patch: Partial<Draft>) => void;
}

export const useAutolabelingStore = create<AutolabelingState>((set) => ({
  scope: "current", indices: "", config: emptyConfig(), configurationLoaded: false, modelClasses: [], inspectedPath: "",
  sessionId: null, runId: null, runs: [], proposals: [], drafts: {}, selectedId: null, visible: true, onlyCurrent: true, offset: 0, total: 0, error: null,
  reset: (sessionId) => set({ sessionId, scope: "current", indices: "", config: emptyConfig(), configurationLoaded: false, modelClasses: [], inspectedPath: "", offset: 0, total: 0, onlyCurrent: true, runId: null, runs: [], proposals: [], drafts: {}, selectedId: null, error: null }),
  selectRun: (runId) => set({ runId, offset: 0, total: 0, proposals: [], drafts: {}, selectedId: null }),
  edit: (proposal, patch) => set((state) => ({
    drafts: { ...state.drafts, [proposal.id]: { ...(state.drafts[proposal.id] ?? { bbox: proposal.bbox, category_id: proposal.category_id }), ...patch } },
    selectedId: proposal.id,
  })),
}));
