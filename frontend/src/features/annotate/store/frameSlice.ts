import { api } from "../../../shared/api/client";
import type { ClassItem, FrameResponse } from "../../../shared/api/types";
import { selectedAfterRemoval } from "./classEdits";
import { FRAME_CHANGE_RESET, type FrameSlice, type Slice } from "./types";

export const createFrameSlice: Slice<FrameSlice> = (set, get) => {
  /** Busca um frame e descarta seleção/trabalho do anterior. */
  const loadFrame = async (request: () => Promise<FrameResponse>) => {
    set({ loading: true });
    try {
      const frame = await request();
      set({ frame, ...FRAME_CHANGE_RESET, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  };

  return {
    frame: null,
    classes: [],
    imageSize: null,
    loading: false,
    error: null,

    fetchFrame: () => loadFrame(() => api.get<FrameResponse>("/frames/current")),
    nextFrame: () => loadFrame(() => api.post<FrameResponse>("/frames/next")),
    prevFrame: () => loadFrame(() => api.post<FrameResponse>("/frames/prev")),

    fetchClasses: async () => {
      try {
        const classes = await api.get<ClassItem[]>("/classes/");
        set({ classes, selectedClassId: classes[0]?.id ?? 0 });
      } catch (e) {
        set({ error: (e as Error).message });
      }
    },

    addClass: async (name, keypoints = []) => {
      try {
        const classes = await api.post<ClassItem[]>("/classes/", { name, keypoints });
        // A classe nova já fica ativa para desenhar.
        set({ classes, selectedClassId: classes[classes.length - 1]?.id ?? 0 });
        return true;
      } catch (e) {
        set({ error: (e as Error).message });
        return false;
      }
    },

    renameClass: async (id, name) => {
      try {
        set({ classes: await api.patch<ClassItem[]>(`/classes/${id}`, { name }) });
        return true;
      } catch (e) {
        set({ error: (e as Error).message });
        return false;
      }
    },

    removeClass: async (id) => {
      try {
        const classes = await api.delete<ClassItem[]>(`/classes/${id}`);
        // Os ids acima do removido mudaram: o desfazer guardaria ids velhos.
        set((s) => ({ classes, selectedClassId: selectedAfterRemoval(s.selectedClassId, id), undoStack: [], redoStack: [] }));
        await loadFrame(() => api.get<FrameResponse>("/frames/current"));
        return true;
      } catch (e) {
        set({ error: (e as Error).message });
        return false;
      }
    },

    setImageSize: (size) => set({ imageSize: size }),

    toggleReviewed: async () => {
      const { frame } = get();
      if (!frame) return;
      try {
        const res = await api.post<{ reviewed: boolean; annotation_count: number }>(
          `/annotations/${frame.index}/reviewed`,
          { reviewed: !frame.reviewed }
        );
        set((s) => ({
          frame: s.frame
            ? { ...s.frame, reviewed: res.reviewed, is_saved: res.reviewed || s.frame.annotations.length > 0 }
            : null,
        }));
      } catch (e) {
        set({ error: `Erro ao marcar frame: ${(e as Error).message}` });
      }
    },

    clearError: () => set({ error: null }),
  };
};
