import { api } from "../../../shared/api/client";
import type { ClassificationResult } from "../../../shared/api/types";
import type { ClassificationSlice, Slice } from "./types";
import { pushUndo } from "./undoSlice";

export const createClassificationSlice: Slice<ClassificationSlice> = (set, get) => ({
  classificationResult: null,
  classKeyBuffer: "",

  setClassKeyBuffer: (value) => set({ classKeyBuffer: value }),

  classifyFrame: async (categoryId) => {
    const { frame } = get();
    if (!frame) return null;
    try {
      const result = await api.post<ClassificationResult>(`/annotations/${frame.index}/classification`, {
        category_id: categoryId,
      });
      set((s) => ({
        classificationResult: result,
        frame: s.frame ? { ...s.frame, classification_id: result.top1_class_id, is_saved: true } : null,
        undoStack: pushUndo(s.undoStack, { kind: "classify", index: frame.index }),
      }));
      return result;
    } catch (e) {
      set({ error: `Erro ao classificar imagem: ${(e as Error).message}` });
      return null;
    }
  },
});
