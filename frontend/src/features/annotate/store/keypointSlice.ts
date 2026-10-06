import { api } from "../../../shared/api/client";
import type { Annotation, Keypoint } from "../../../shared/api/types";
import type { KeypointSlice, KeypointWip, Slice } from "./types";
import { pushUndo } from "./undoSlice";

const ABSENT: Keypoint = [0, 0, 0];

export const createKeypointSlice: Slice<KeypointSlice> = (set, get) => {
  /** Grava a instância em andamento (pontos não marcados ficam ausentes). */
  const commit = async (wip: KeypointWip) => {
    const { frame } = get();
    set({ kpWip: null });
    if (!frame) return;
    if (!wip.points.some((p) => p[2] > 0)) {
      set({ error: "Instância sem nenhum ponto marcado — descartada." });
      return;
    }
    try {
      const ann = await api.post<Annotation>(`/annotations/${frame.index}`, {
        category_id: wip.categoryId,
        keypoints: wip.points,
        source: "manual",
      });
      set((s) => ({
        frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, ann], is_saved: true } : null,
        selectedAnnotationId: ann.id,
        selectedKpIndex: null,
        undoStack: pushUndo(s.undoStack, { kind: "add", index: frame.index, annId: ann.id }),
      }));
    } catch (e) {
      set({ error: `Erro ao salvar instância: ${(e as Error).message}` });
    }
  };

  /** Avança para o próximo ponto; ao passar do último, grava a instância. */
  const advance = async (next: KeypointWip) => {
    set({ kpWip: next });
    if (next.index >= next.points.length) await commit(next);
  };

  return {
    kpWip: null,
    kpNextVisibility: 2,
    selectedKpIndex: null,

    kpPlacePoint: async (x, y) => {
      const { kpWip, selectedClassId, classes, kpNextVisibility } = get();
      const names = classes.find((c) => c.id === selectedClassId)?.keypoints ?? [];
      let wip = kpWip;
      if (!wip) {
        if (names.length === 0) {
          set({ error: "Esta classe não tem pontos definidos." });
          return;
        }
        wip = { categoryId: selectedClassId, points: names.map(() => ABSENT), index: 0 };
      }
      const current = wip;
      const points = current.points.map((p, i) => (i === current.index ? ([x, y, kpNextVisibility] as Keypoint) : p));
      set({ selectedAnnotationId: null, selectedKpIndex: null });
      await advance({ ...current, points, index: current.index + 1 });
    },

    kpSkipPoint: async () => {
      const wip = get().kpWip;
      if (wip) await advance({ ...wip, index: wip.index + 1 });   // o ponto já está ausente
    },

    kpUndoPoint: () => {
      const wip = get().kpWip;
      if (!wip) return false;
      if (wip.index <= 1) {
        set({ kpWip: null });
        return true;
      }
      const index = wip.index - 1;
      set({ kpWip: { ...wip, points: wip.points.map((p, i) => (i === index ? ABSENT : p)), index } });
      return true;
    },

    kpCancel: () => set({ kpWip: null }),

    kpFinish: async () => {
      const wip = get().kpWip;
      if (wip) await commit(wip);
    },

    kpToggleVisibility: async () => {
      const { frame, selectedAnnotationId, selectedKpIndex, kpNextVisibility, updateAnnotation } = get();
      const ann = frame?.annotations.find((a) => a.id === selectedAnnotationId);
      const point = selectedKpIndex !== null ? ann?.keypoints?.[selectedKpIndex] : undefined;
      if (ann?.keypoints && point && point[2] > 0) {
        // Ponto marcado alterna entre visível e oculto; nunca some (ausente é com X).
        const keypoints = ann.keypoints.map((p, i) =>
          i === selectedKpIndex ? ([p[0], p[1], p[2] === 2 ? 1 : 2] as Keypoint) : p
        );
        await updateAnnotation(ann.id, { keypoints });
        return;
      }
      set({ kpNextVisibility: kpNextVisibility === 2 ? 1 : 2 });
    },

    kpMovePoint: async (annId, index, x, y) => {
      const ann = get().frame?.annotations.find((a) => a.id === annId);
      if (!ann?.keypoints) return;
      const keypoints = ann.keypoints.map((p, i) => (i === index ? ([x, y, p[2] || 2] as Keypoint) : p));
      await get().updateAnnotation(annId, { keypoints });
    },

    selectKeypoint: (annId, index) => set({ selectedAnnotationId: annId, selectedKpIndex: index }),
  };
};
