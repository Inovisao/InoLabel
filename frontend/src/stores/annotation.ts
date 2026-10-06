import { create } from "zustand";
import { api } from "../api/client";
import type {
  Annotation,
  AnnotationPatch,
  ClassItem,
  ClassificationResult,
  FrameResponse,
} from "../api/types";
import { useSessionStore } from "./session";

export type Tool = "box" | "select";

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
  classKeyBuffer: "",
  loading: false,
  error: null,

  fetchFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.get<FrameResponse>("/frames/current");
      set({ frame, classificationResult: null, selectedAnnotationId: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  nextFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/next");
      set({ frame, classificationResult: null, selectedAnnotationId: null, loading: false });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },

  prevFrame: async () => {
    set({ loading: true });
    try {
      const frame = await api.post<FrameResponse>("/frames/prev");
      set({ frame, classificationResult: null, selectedAnnotationId: null, loading: false });
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
      if ("bbox" in patch) before.bbox = current.bbox;
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

  selectAnnotation: (annId) => set({ selectedAnnotationId: annId }),

  setTool: (tool) => set({ tool }),

  setClassKeyBuffer: (value) => set({ classKeyBuffer: value }),

  resetSessionUi: () =>
    set({ selectedAnnotationId: null, undoStack: [], pinnedTrackId: null, classKeyBuffer: "", tool: "box" }),

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
        set({ frame, classificationResult: null, selectedAnnotationId: null });
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
