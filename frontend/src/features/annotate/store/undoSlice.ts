import { api } from "../../../shared/api/client";
import type { Annotation, AnnotationPatch, ClassificationResult, FrameResponse } from "../../../shared/api/types";
import { createPayload } from "./selection";
import { FRAME_CHANGE_RESET, type AnnotationState, type Slice, type UndoEntry, type UndoSlice } from "./types";

const UNDO_LIMIT = 100;

/** Empilha a operação (mantém as últimas UNDO_LIMIT). */
export function pushUndo(stack: UndoEntry[], entry: UndoEntry): UndoEntry[] {
  return [...stack, entry].slice(-UNDO_LIMIT);
}

/** Edição nova: entra no Ctrl+Z e esvazia o Ctrl+Y (o que foi desfeito não volta mais). */
export function recordUndo(s: Pick<AnnotationState, "undoStack">, entry: UndoEntry) {
  return { undoStack: pushUndo(s.undoStack, entry), redoStack: [] as UndoEntry[] };
}

/** Valores atuais dos campos que o PATCH altera: aplicados depois, desfazem o PATCH. */
export function previousValues(current: Annotation, patch: AnnotationPatch): AnnotationPatch {
  const before: AnnotationPatch = {};
  if ("category_id" in patch) before.category_id = current.category_id;
  if ("track_id" in patch) before.track_id = current.track_id ?? null;
  // No OBB a geometria volta pelo obb (ângulo + posição); o backend refaz o bbox.
  if (("bbox" in patch || "obb" in patch) && current.obb) before.obb = current.obb;
  else if ("keypoints" in patch && current.keypoints) before.keypoints = current.keypoints;
  else if ("bbox" in patch) before.bbox = current.bbox;
  return before;
}

/** Recria a anotação como era (inclusive origem e score de uma predição do modelo). */
const restorePayload = (ann: Annotation) => ({
  ...createPayload(ann),
  source: ann.source,
  ...(ann.score != null ? { score: ann.score } : {}),
});

/**
 * Ctrl+Z e Ctrl+Y. Cada entrada descreve como voltar uma operação; aplicá-la devolve a
 * entrada inversa, que vai para a outra pilha. Assim desfazer e refazer são a mesma
 * operação, em direções opostas.
 */
export const createUndoSlice: Slice<UndoSlice> = (set, get) => {
  const findAnn = (id: number) => get().frame?.annotations.find((a) => a.id === id);

  /** Aplica a entrada no frame dela e devolve a entrada que a reverte (null se não houver). */
  const apply = async (entry: UndoEntry): Promise<UndoEntry | null> => {
    // Vai ao frame da operação antes de aplicá-la.
    if (get().frame?.index !== entry.index) {
      const frame = await api.post<FrameResponse>(`/frames/goto/${entry.index}`);
      set({ frame, ...FRAME_CHANGE_RESET });
    }
    const { index } = entry;

    if (entry.kind === "add") {
      const ann = findAnn(entry.annId);
      await get().removeAnnotation(entry.annId, { skipUndo: true });
      return ann ? { kind: "remove", index, ann } : null;
    }
    if (entry.kind === "remove") {
      const restored = await api.post<Annotation>(`/annotations/${index}`, restorePayload(entry.ann));
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, restored], is_saved: true } : null,
        selectedAnnotationId: restored.id,
        selectedIds: [restored.id],
      }));
      return { kind: "add", index, annId: restored.id };
    }
    if (entry.kind === "update") {
      const current = findAnn(entry.annId);
      const updated = await api.patch<Annotation>(`/annotations/${index}/${entry.annId}`, entry.before);
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: s.frame.annotations.map((a) => (a.id === entry.annId ? updated : a)) } : null,
      }));
      return current ? { kind: "update", index, annId: entry.annId, before: previousValues(current, entry.before) } : null;
    }
    if (entry.kind === "addMany") {
      const anns = entry.annIds.map(findAnn).filter((a): a is Annotation => !!a);
      await api.post(`/annotations/${index}/batch-delete`, { ids: entry.annIds });
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: s.frame.annotations.filter((a) => !entry.annIds.includes(a.id)) } : null,
        selectedIds: [],
        selectedAnnotationId: null,
      }));
      return anns.length ? { kind: "removeMany", index, anns } : null;
    }
    if (entry.kind === "updateMany") {
      const inverse = entry.before.flatMap(({ id, changes }) => {
        const current = findAnn(id);
        return current ? [{ id, changes: previousValues(current, changes) }] : [];
      });
      const updated = await api.patch<Annotation[]>(`/annotations/${index}/batch`, { updates: entry.before });
      const byId = new Map(updated.map((a) => [a.id, a]));
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: s.frame.annotations.map((a) => byId.get(a.id) ?? a) } : null,
      }));
      return inverse.length ? { kind: "updateMany", index, before: inverse } : null;
    }
    if (entry.kind === "removeMany") {
      const res = await api.post<{ annotations: Annotation[] }>(`/annotations/${index}/batch`, {
        annotations: entry.anns.map(restorePayload),
      });
      const ids = res.annotations.map((a) => a.id);
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, ...res.annotations], is_saved: true } : null,
        selectedIds: ids,
        selectedAnnotationId: ids[ids.length - 1] ?? null,
      }));
      return { kind: "addMany", index, annIds: ids };
    }
    if (entry.kind === "reclassify") {
      const result = await api.post<ClassificationResult>(`/annotations/${index}/classification`, {
        category_id: entry.categoryId,
      });
      set((s) => ({
        classificationResult: result,
        frame: s.frame ? { ...s.frame, classification_id: result.top1_class_id, is_saved: true } : null,
      }));
      return { kind: "classify", index, categoryId: entry.categoryId };
    }
    // classify
    await api.delete(`/annotations/${index}/classification`);
    set((s) => ({
      classificationResult: null,
      frame: s.frame
        ? { ...s.frame, classification_id: null, is_saved: s.frame.annotations.length > 0 || !!s.frame.reviewed }
        : null,
    }));
    return entry.categoryId != null ? { kind: "reclassify", index, categoryId: entry.categoryId } : null;
  };

  /** Tira a última entrada de uma pilha, aplica e guarda a inversa na outra. */
  const step = async (from: "undoStack" | "redoStack", to: "undoStack" | "redoStack", verb: string) => {
    const stack = get()[from];
    const entry = stack[stack.length - 1];
    if (!entry) return;
    set({ [from]: stack.slice(0, -1) } as Pick<UndoSlice, typeof from>);
    try {
      const inverse = await apply(entry);
      if (inverse) set((s) => ({ [to]: pushUndo(s[to], inverse) }) as Pick<UndoSlice, typeof to>);
    } catch (e) {
      set({ error: `Não foi possível ${verb}: ${(e as Error).message}` });
    }
  };

  return {
    undoStack: [],
    redoStack: [],
    undo: () => step("undoStack", "redoStack", "desfazer"),
    redo: () => step("redoStack", "undoStack", "refazer"),
  };
};
