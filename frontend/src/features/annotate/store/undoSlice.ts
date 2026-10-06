import { api } from "../../../shared/api/client";
import type { Annotation, FrameResponse } from "../../../shared/api/types";
import { FRAME_CHANGE_RESET, type Slice, type UndoEntry, type UndoSlice } from "./types";

const UNDO_LIMIT = 100;

/** Empilha a operação para o Ctrl+Z (mantém as últimas UNDO_LIMIT). */
export function pushUndo(stack: UndoEntry[], entry: UndoEntry): UndoEntry[] {
  return [...stack, entry].slice(-UNDO_LIMIT);
}

export const createUndoSlice: Slice<UndoSlice> = (set, get) => ({
  undoStack: [],

  undo: async () => {
    const stack = get().undoStack;
    const entry = stack[stack.length - 1];
    if (!entry) return;
    set({ undoStack: stack.slice(0, -1) });
    try {
      // Volta ao frame da operação antes de desfazê-la.
      if (get().frame?.index !== entry.index) {
        const frame = await api.post<FrameResponse>(`/frames/goto/${entry.index}`);
        set({ frame, ...FRAME_CHANGE_RESET });
      }
      if (entry.kind === "add") {
        await get().removeAnnotation(entry.annId, { skipUndo: true });
      } else if (entry.kind === "remove") {
        const { ann } = entry;
        const restored = await api.post<Annotation>(`/annotations/${entry.index}`, {
          category_id: ann.category_id,
          bbox: ann.bbox,
          obb: ann.obb ?? undefined,
          source: ann.source,
          score: ann.score ?? undefined,
          keypoints: ann.keypoints ?? undefined,
          ...(ann.track_id != null ? { track_id: ann.track_id } : {}),
        });
        set((s) => ({
          frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, restored], is_saved: true } : null,
          selectedAnnotationId: restored.id,
        }));
      } else if (entry.kind === "update") {
        const updated = await api.patch<Annotation>(`/annotations/${entry.index}/${entry.annId}`, entry.before);
        set((s) => ({
          frame: s.frame
            ? { ...s.frame, annotations: s.frame.annotations.map((a) => (a.id === entry.annId ? updated : a)) }
            : null,
        }));
      } else {
        await api.delete(`/annotations/${entry.index}/classification`);
        set((s) => ({
          classificationResult: null,
          frame: s.frame
            ? { ...s.frame, classification_id: null, is_saved: s.frame.annotations.length > 0 || !!s.frame.reviewed }
            : null,
        }));
      }
    } catch (e) {
      set({ error: `Não foi possível desfazer: ${(e as Error).message}` });
    }
  },
});
