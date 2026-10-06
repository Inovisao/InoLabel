import { create } from "zustand";
import { api } from "../api/client";
import type {
  Annotation,
  AnnotationPatch,
  ClassItem,
  ClassificationResult,
  FrameResponse,
  Keypoint,
} from "../api/types";
import { useSessionStore } from "./session";
import { normalizeAngle, rotateTo } from "../components/canvas/obbGeometry";

export type Tool = "box" | "select";

/** Modo keypoint: instância sendo marcada, ponto a ponto, na ordem da classe. */
export interface KeypointWip {
  categoryId: number;
  points: Keypoint[];
  /** Próximo ponto a marcar (índice em `points`). */
  index: number;
}

/** Visibilidade COCO: 2 visível, 1 oculto (marcado, mas encoberto), 0 ausente. */
export type KeypointVisibility = 1 | 2;

/** Uma operação desfazível; guarda o frame para desfazer mesmo após navegar. */
type UndoEntry =
  | { kind: "add"; index: number; annId: number }
  | { kind: "remove"; index: number; ann: Annotation }
  | { kind: "update"; index: number; annId: number; before: AnnotationPatch }
  | { kind: "classify"; index: number };

const UNDO_LIMIT = 100;

interface AnnotationState {
  frame: FrameResponse | null;
  classes: ClassItem[];
  classificationResult: ClassificationResult | null;
  selectedClassId: number;
  /** Anotação selecionada para editar (classe, ID, mover, apagar). */
  selectedAnnotationId: number | null;
  tool: Tool;
  /** ID fixo para as próximas caixas no tracking; null = próximo ID livre. */
  pinnedTrackId: number | null;
  undoStack: UndoEntry[];
  kpWip: KeypointWip | null;
  /** Visibilidade dada aos próximos pontos marcados (tecla C alterna). */
  kpNextVisibility: KeypointVisibility;
  /** Ponto selecionado da instância selecionada (arrastar, C, etc.). */
  selectedKpIndex: number | null;
  /** Tamanho da imagem exibida (px), para manter caixas OBB dentro dela. */
  imageSize: { width: number; height: number } | null;
  /** Número de classe sendo digitado na classificação (> 9 classes). */
  classKeyBuffer: string;
  loading: boolean;
  error: string | null;
  fetchFrame: () => Promise<void>;
  nextFrame: () => Promise<void>;
  prevFrame: () => Promise<void>;
  fetchClasses: () => Promise<void>;
  setSelectedClass: (id: number) => void;
  addAnnotation: (bbox: [number, number, number, number]) => Promise<void>;
  updateAnnotation: (annId: number, patch: AnnotationPatch) => Promise<void>;
  selectAnnotation: (annId: number | null) => void;
  setTool: (tool: Tool) => void;
  setClassKeyBuffer: (value: string) => void;
  setImageSize: (size: { width: number; height: number } | null) => void;
  /** Keypoint: marca o próximo ponto da instância em andamento (cria a instância se preciso). */
  kpPlacePoint: (x: number, y: number) => Promise<void>;
  /** Keypoint: marca o próximo ponto como ausente (tecla X). */
  kpSkipPoint: () => Promise<void>;
  /** Keypoint: desfaz o último ponto da instância em andamento; false se não havia. */
  kpUndoPoint: () => boolean;
  kpCancel: () => void;
  /** Keypoint: fecha a instância agora; pontos que faltam ficam ausentes (tecla F). */
  kpFinish: () => Promise<void>;
  /** Keypoint: alterna visível/oculto do ponto selecionado, ou dos próximos pontos (tecla C). */
  kpToggleVisibility: () => Promise<void>;
  kpMovePoint: (annId: number, index: number, x: number, y: number) => Promise<void>;
  selectKeypoint: (annId: number, index: number | null) => void;
  /** Modo OBB: gira a caixa selecionada para `angle` (absoluto) ou por `delta` graus. */
  rotateSelected: (opts: { angle?: number; delta?: number }) => Promise<void>;
  /** Limpa seleção, desfazer e ID fixado ao abrir uma sessão. */
  resetSessionUi: () => void;
  setPinnedTrackId: (id: number | null) => void;
  fetchNextTrackId: () => Promise<number | null>;
  classifyFrame: (categoryId: number) => Promise<ClassificationResult | null>;
  /** Marca/desmarca o frame como revisado (negativo: revisado sem objetos). */
  toggleReviewed: () => Promise<void>;
  removeAnnotation: (annId: number, opts?: { skipUndo?: boolean }) => Promise<void>;
  undo: () => Promise<void>;
  clearError: () => void;
}

export const useAnnotationStore = create<AnnotationState>((set, get) => ({
  frame: null,
  classes: [],
  classificationResult: null,
  selectedClassId: 0,
  selectedAnnotationId: null,
  tool: "box",
  pinnedTrackId: null,
  undoStack: [],
  kpWip: null,
  kpNextVisibility: 2,
  selectedKpIndex: null,
  classKeyBuffer: "",
  imageSize: null,
  loading: false,
  error: null,

  fetchFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.get<FrameResponse>("/frames/current");
      set({ frame, classificationResult: null, selectedAnnotationId: null, selectedKpIndex: null, kpWip: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  nextFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/next");
      set({ frame, classificationResult: null, selectedAnnotationId: null, selectedKpIndex: null, kpWip: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  prevFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/prev");
      set({ frame, classificationResult: null, selectedAnnotationId: null, selectedKpIndex: null, kpWip: null, loading: false });
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
        frame: s.frame
          ? {
              ...s.frame,
              annotations: [...s.frame.annotations, ann],
              is_saved: true,
            }
          : null,
        selectedAnnotationId: ann.id,
        undoStack: pushUndo(s.undoStack, { kind: "add", index: frame.index, annId: ann.id }),
      }));
    } catch (e) {
      set({ error: `Erro ao salvar anotação: ${(e as Error).message}` });
    }
  },

  updateAnnotation: async (annId, patch) => {
    const { frame } = get();
    if (!frame) return;
    const current = frame.annotations.find((a) => a.id === annId);
    if (!current) return;
    try {
      const updated = await api.patch<Annotation>(`/annotations/${frame.index}/${annId}`, patch);
      const before: AnnotationPatch = {};
      if ("category_id" in patch) before.category_id = current.category_id;
      if ("track_id" in patch) before.track_id = current.track_id ?? null;
      // No OBB a geometria volta pelo obb (ângulo + posição); o backend refaz o bbox.
      if (("bbox" in patch || "obb" in patch) && current.obb) before.obb = current.obb;
      else if ("keypoints" in patch && current.keypoints) before.keypoints = current.keypoints;
      else if ("bbox" in patch) before.bbox = current.bbox;
      set((s) => ({
        frame: s.frame
          ? { ...s.frame, annotations: s.frame.annotations.map((a) => (a.id === annId ? updated : a)) }
          : null,
        undoStack: pushUndo(s.undoStack, { kind: "update", index: frame.index, annId, before }),
      }));
    } catch (e) {
      set({ error: `Erro ao editar anotação: ${(e as Error).message}` });
    }
  },

  selectAnnotation: (annId) => set({ selectedAnnotationId: annId, selectedKpIndex: null }),

  setTool: (tool) => set({ tool }),

  setClassKeyBuffer: (value) => set({ classKeyBuffer: value }),

  setImageSize: (size) => set({ imageSize: size }),

  kpPlacePoint: async (x, y) => {
    const { kpWip, selectedClassId, classes, kpNextVisibility } = get();
    const names = classes.find((c) => c.id === selectedClassId)?.keypoints ?? [];
    let wip = kpWip;
    if (!wip) {
      if (names.length === 0) {
        set({ error: "Esta classe não tem pontos definidos." });
        return;
      }
      wip = { categoryId: selectedClassId, points: names.map(() => [0, 0, 0] as Keypoint), index: 0 };
    }
    const points = wip.points.map((p, i) => (i === wip!.index ? ([x, y, kpNextVisibility] as Keypoint) : p));
    const next = { ...wip, points, index: wip.index + 1 };
    set({ kpWip: next, selectedAnnotationId: null, selectedKpIndex: null });
    if (next.index >= next.points.length) await commitWip(next);
  },

  kpSkipPoint: async () => {
    const wip = get().kpWip;
    if (!wip) return;
    const next = { ...wip, index: wip.index + 1 };   // o ponto já está [0, 0, 0]
    set({ kpWip: next });
    if (next.index >= next.points.length) await commitWip(next);
  },

  kpUndoPoint: () => {
    const wip = get().kpWip;
    if (!wip) return false;
    if (wip.index <= 1) {
      set({ kpWip: null });
      return true;
    }
    const index = wip.index - 1;
    const points = wip.points.map((p, i) => (i === index ? ([0, 0, 0] as Keypoint) : p));
    set({ kpWip: { ...wip, points, index } });
    return true;
  },

  kpCancel: () => set({ kpWip: null }),

  kpFinish: async () => {
    const wip = get().kpWip;
    if (wip) await commitWip(wip);
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

  resetSessionUi: () =>
    set({
      selectedAnnotationId: null,
      undoStack: [],
      pinnedTrackId: null,
      classKeyBuffer: "",
      tool: "box",
      kpWip: null,
      kpNextVisibility: 2,
      selectedKpIndex: null,
    }),

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

  classifyFrame: async (categoryId) => {
    const { frame } = get();
    if (!frame) return null;
    try {
      const result = await api.post<ClassificationResult>(
        `/annotations/${frame.index}/classification`,
        { category_id: categoryId }
      );
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
          frame: {
            ...s.frame,
            annotations: remaining,
            is_saved: remaining.length > 0 || !!s.frame.reviewed,
          },
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

  undo: async () => {
    const stack = get().undoStack;
    const entry = stack[stack.length - 1];
    if (!entry) return;
    set({ undoStack: stack.slice(0, -1) });
    try {
      // Volta ao frame da operação antes de desfazê-la.
      if (get().frame?.index !== entry.index) {
        const frame = await api.post<FrameResponse>(`/frames/goto/${entry.index}`);
        set({ frame, classificationResult: null, selectedAnnotationId: null, selectedKpIndex: null, kpWip: null });
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

  clearError: () => set({ error: null }),
}));


function pushUndo(stack: UndoEntry[], entry: UndoEntry): UndoEntry[] {
  return [...stack, entry].slice(-UNDO_LIMIT);
}


/** Grava a instância de keypoint em andamento (pontos não marcados ficam ausentes). */
async function commitWip(wip: KeypointWip): Promise<void> {
  const store = useAnnotationStore;
  const { frame } = store.getState();
  store.setState({ kpWip: null });
  if (!frame) return;
  if (!wip.points.some((p) => p[2] > 0)) {
    store.setState({ error: "Instância sem nenhum ponto marcado — descartada." });
    return;
  }
  try {
    const ann = await api.post<Annotation>(`/annotations/${frame.index}`, {
      category_id: wip.categoryId,
      keypoints: wip.points,
      source: "manual",
    });
    store.setState((s) => ({
      frame: s.frame ? { ...s.frame, annotations: [...s.frame.annotations, ann], is_saved: true } : null,
      selectedAnnotationId: ann.id,
      selectedKpIndex: null,
      undoStack: pushUndo(s.undoStack, { kind: "add", index: frame.index, annId: ann.id }),
    }));
  } catch (e) {
    store.setState({ error: `Erro ao salvar instância: ${(e as Error).message}` });
  }
}
