import { create } from "zustand";
import { api } from "../api/client";
import type { Annotation, ClassItem, FrameResponse } from "../api/types";

interface AnnotationState {
  frame: FrameResponse | null;
  classes: ClassItem[];
  selectedClassId: number;
  loading: boolean;
  fetchFrame: () => Promise<void>;
  nextFrame: () => Promise<void>;
  prevFrame: () => Promise<void>;
  fetchClasses: () => Promise<void>;
  setSelectedClass: (id: number) => void;
  addAnnotation: (bbox: [number, number, number, number]) => Promise<void>;
  removeAnnotation: (annId: number) => Promise<void>;
}

export const useAnnotationStore = create<AnnotationState>((set, get) => ({
  frame: null,
  classes: [],
  selectedClassId: 0,
  loading: false,

  fetchFrame: async () => {
    set({ loading: true });
    const frame = await api.get<FrameResponse>("/frames/current");
    set({ frame, loading: false });
  },

  nextFrame: async () => {
    set({ loading: true });
    const frame = await api.post<FrameResponse>("/frames/next");
    set({ frame, loading: false });
  },

  prevFrame: async () => {
    set({ loading: true });
    const frame = await api.post<FrameResponse>("/frames/prev");
    set({ frame, loading: false });
  },

  fetchClasses: async () => {
    const classes = await api.get<ClassItem[]>("/classes/");
    set({ classes, selectedClassId: classes[0]?.id ?? 0 });
  },

  setSelectedClass: (id) => set({ selectedClassId: id }),

  addAnnotation: async (bbox) => {
    const { frame, selectedClassId } = get();
    if (!frame) return;
    const ann = await api.post<Annotation>(`/annotations/${frame.index}`, {
      category_id: selectedClassId,
      bbox,
      source: "manual",
    });
    set((s) => ({
      frame: s.frame
        ? { ...s.frame, annotations: [...s.frame.annotations, ann] }
        : null,
    }));
  },

  removeAnnotation: async (annId) => {
    const { frame } = get();
    if (!frame) return;
    await api.delete(`/annotations/${frame.index}/${annId}`);
    set((s) => ({
      frame: s.frame
        ? {
            ...s.frame,
            annotations: s.frame.annotations.filter((a) => a.id !== annId),
          }
        : null,
    }));
  },
}));
