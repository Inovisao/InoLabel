import { create } from "zustand";
import { api } from "../api/client";
import type { Annotation, ClassItem, ClassificationResult, FrameResponse } from "../api/types";

interface AnnotationState {
  frame: FrameResponse | null;
  classes: ClassItem[];
  classificationResult: ClassificationResult | null;
  selectedClassId: number;
  loading: boolean;
  error: string | null;
  fetchFrame: () => Promise<void>;
  nextFrame: () => Promise<void>;
  prevFrame: () => Promise<void>;
  fetchClasses: () => Promise<void>;
  setSelectedClass: (id: number) => void;
  addAnnotation: (bbox: [number, number, number, number]) => Promise<void>;
  classifyFrame: (categoryId: number) => Promise<ClassificationResult | null>;
  removeAnnotation: (annId: number) => Promise<void>;
  clearError: () => void;
}

export const useAnnotationStore = create<AnnotationState>((set, get) => ({
  frame: null,
  classes: [],
  classificationResult: null,
  selectedClassId: 0,
  loading: false,
  error: null,

  fetchFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.get<FrameResponse>("/frames/current");
      set({ frame, classificationResult: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  nextFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/next");
      set({ frame, classificationResult: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  prevFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/prev");
      set({ frame, classificationResult: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  fetchClasses: async () => {
    try {
      const classes = await api.get<ClassItem[]>("/classes/");
      set({ classes, selectedClassId: classes[0]?.id ?? 0 });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  setSelectedClass: (id) => set({ selectedClassId: id }),

  addAnnotation: async (bbox) => {
    const { frame, selectedClassId } = get();
    if (!frame) return;
    try {
      const ann = await api.post<Annotation>(`/annotations/${frame.index}`, {
        category_id: selectedClassId,
        bbox,
        source: "manual",
      });
      set((s) => ({
        frame: s.frame
          ? {
              ...s.frame,
              annotations: [...s.frame.annotations, ann],
              is_saved: true,
            }
          : null,
      }));
    } catch (e) {
      set({ error: `Erro ao salvar anotação: ${(e as Error).message}` });
    }
  },

  classifyFrame: async (categoryId) => {
    const { frame } = get();
    if (!frame) return null;
    try {
      const result = await api.post<ClassificationResult>(
        `/annotations/${frame.index}/classification`,
        { category_id: categoryId }
      );
      set({ classificationResult: result });
      return result;
    } catch (e) {
      set({ error: `Erro ao classificar imagem: ${(e as Error).message}` });
      return null;
    }
  },

  removeAnnotation: async (annId) => {
    const { frame } = get();
    if (!frame) return;
    try {
      await api.delete(`/annotations/${frame.index}/${annId}`);
      set((s) => {
        if (!s.frame) return {};
        const remaining = s.frame.annotations.filter((a) => a.id !== annId);
        return {
          frame: {
            ...s.frame,
            annotations: remaining,
            is_saved: remaining.length > 0,
          },
        };
      });
    } catch (e) {
      set({ error: `Erro ao remover anotação: ${(e as Error).message}` });
    }
  },

  clearError: () => set({ error: null }),
}));
