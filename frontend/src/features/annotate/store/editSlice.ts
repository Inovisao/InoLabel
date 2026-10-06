import { api } from "../../../shared/api/client";
import type { Annotation, AnnotationPatch } from "../../../shared/api/types";
import { useSessionStore } from "../../../shared/session/store";
import { normalizeAngle, rotateTo } from "../canvas/obbGeometry";
import type { EditSlice, Slice } from "./types";
import { pushUndo } from "./undoSlice";

/** Valores anteriores dos campos alterados, para o Ctrl+Z refazer o PATCH ao contrário. */
function previousValues(current: Annotation, patch: AnnotationPatch): AnnotationPatch {
  const before: AnnotationPatch = {};
  if ("category_id" in patch) before.category_id = current.category_id;
  if ("track_id" in patch) before.track_id = current.track_id ?? null;
  // No OBB a geometria volta pelo obb (ângulo + posição); o backend refaz o bbox.
  if (("bbox" in patch || "obb" in patch) && current.obb) before.obb = current.obb;
  else if ("keypoints" in patch && current.keypoints) before.keypoints = current.keypoints;
  else if ("bbox" in patch) before.bbox = current.bbox;
  return before;
}

export const createEditSlice: Slice<EditSlice> = (set, get) => ({
  selectedClassId: 0,
  selectedAnnotationId: null,
  tool: "box",
  pinnedTrackId: null,

  setSelectedClass: (id) => {
    // Trocar de classe no meio de uma instância de keypoint a descarta (pontos de outra classe).
    const wip = get().kpWip;
    if (wip && wip.categoryId !== id && wip.index > 0) {
      set({ selectedClassId: id, kpWip: null, error: "Instância em andamento descartada ao trocar de classe." });
      return;
    }
    set({ selectedClassId: id, kpWip: null });
  },

  addAnnotation: async (bbox) => {
    const { frame, selectedClassId, pinnedTrackId } = get();
    if (!frame) return;
    try {
      // No tracking toda caixa nasce com ID: o fixado ou o próximo livre.
      let trackId: number | null = null;
      if (useSessionStore.getState().mode === "tracking") {
        trackId = pinnedTrackId ?? (await get().fetchNextTrackId());
      }
      const ann = await api.post<Annotation>(`/annotations/${frame.index}`, {
        category_id: selectedClassId,
        bbox,
        source: "manual",
        ...(trackId !== null ? { track_id: trackId } : {}),
      });
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, ann], is_saved: true } : null,
        selectedAnnotationId: ann.id,
        undoStack: pushUndo(s.undoStack, { kind: "add", index: frame.index, annId: ann.id }),
      }));
    } catch (e) {
      set({ error: `Erro ao salvar anotação: ${(e as Error).message}` });
    }
  },

  updateAnnotation: async (annId, patch) => {
    const { frame } = get();
    const current = frame?.annotations.find((a) => a.id === annId);
    if (!frame || !current) return;
    try {
      const updated = await api.patch<Annotation>(`/annotations/${frame.index}/${annId}`, patch);
      set((s) => ({
        frame: s.frame
          ? { ...s.frame, annotations: s.frame.annotations.map((a) => (a.id === annId ? updated : a)) }
          : null,
        undoStack: pushUndo(s.undoStack, {
          kind: "update",
          index: frame.index,
          annId,
          before: previousValues(current, patch),
        }),
      }));
    } catch (e) {
      set({ error: `Erro ao editar anotação: ${(e as Error).message}` });
    }
  },

  removeAnnotation: async (annId, opts) => {
    const { frame } = get();
    if (!frame) return;
    const removed = frame.annotations.find((a) => a.id === annId);
    try {
      await api.delete(`/annotations/${frame.index}/${annId}`);
      set((s) => {
        if (!s.frame) return {};
        const remaining = s.frame.annotations.filter((a) => a.id !== annId);
        return {
          frame: { ...s.frame, annotations: remaining, is_saved: remaining.length > 0 || !!s.frame.reviewed },
          selectedAnnotationId: s.selectedAnnotationId === annId ? null : s.selectedAnnotationId,
          undoStack:
            removed && !opts?.skipUndo
              ? pushUndo(s.undoStack, { kind: "remove", index: frame.index, ann: removed })
              : s.undoStack,
        };
      });
    } catch (e) {
      set({ error: `Erro ao remover anotação: ${(e as Error).message}` });
    }
  },

  selectAnnotation: (annId) => set({ selectedAnnotationId: annId, selectedKpIndex: null }),

  setTool: (tool) => set({ tool }),

  setPinnedTrackId: (id) => set({ pinnedTrackId: id }),

  fetchNextTrackId: async () => {
    try {
      const res = await api.get<{ next_track_id: number }>("/annotations/next-track-id");
      return res.next_track_id;
    } catch (e) {
      set({ error: `Erro ao obter próximo ID: ${(e as Error).message}` });
      return null;
    }
  },

  rotateSelected: async ({ angle, delta }) => {
    const { frame, selectedAnnotationId, imageSize, updateAnnotation } = get();
    const ann = frame?.annotations.find((a) => a.id === selectedAnnotationId);
    if (!ann?.obb || !imageSize) return;
    const target = normalizeAngle(angle ?? ann.obb.angle + (delta ?? 0));
    const rotated = rotateTo(ann.obb, target, imageSize.width, imageSize.height);
    if (!rotated) {
      set({ error: "A caixa não cabe na imagem nesse ângulo." });
      return;
    }
    await updateAnnotation(ann.id, { obb: rotated });
  },
});
