import type { StateCreator } from "zustand";
import type {
  Annotation,
  AnnotationPatch,
  ClassItem,
  ClassificationResult,
  FrameResponse,
  Keypoint,
} from "../../../shared/api/types";

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
export type UndoEntry =
  | { kind: "add"; index: number; annId: number }
  | { kind: "remove"; index: number; ann: Annotation }
  | { kind: "update"; index: number; annId: number; before: AnnotationPatch }
  | { kind: "classify"; index: number };

export interface FrameSlice {
  frame: FrameResponse | null;
  classes: ClassItem[];
  /** Tamanho da imagem exibida (px), para manter caixas OBB dentro dela. */
  imageSize: { width: number; height: number } | null;
  loading: boolean;
  error: string | null;
  fetchFrame: () => Promise<void>;
  nextFrame: () => Promise<void>;
  prevFrame: () => Promise<void>;
  fetchClasses: () => Promise<void>;
  setImageSize: (size: { width: number; height: number } | null) => void;
  /** Marca/desmarca o frame como revisado (negativo: revisado sem objetos). */
  toggleReviewed: () => Promise<void>;
  clearError: () => void;
}

export interface EditSlice {
  selectedClassId: number;
  /** Anotação selecionada para editar (classe, ID, mover, apagar). */
  selectedAnnotationId: number | null;
  tool: Tool;
  /** ID fixo para as próximas caixas no tracking; null = próximo ID livre. */
  pinnedTrackId: number | null;
  setSelectedClass: (id: number) => void;
  addAnnotation: (bbox: [number, number, number, number]) => Promise<void>;
  updateAnnotation: (annId: number, patch: AnnotationPatch) => Promise<void>;
  removeAnnotation: (annId: number, opts?: { skipUndo?: boolean }) => Promise<void>;
  selectAnnotation: (annId: number | null) => void;
  setTool: (tool: Tool) => void;
  setPinnedTrackId: (id: number | null) => void;
  fetchNextTrackId: () => Promise<number | null>;
  /** Modo OBB: gira a caixa selecionada para `angle` (absoluto) ou por `delta` graus. */
  rotateSelected: (opts: { angle?: number; delta?: number }) => Promise<void>;
}

export interface UndoSlice {
  undoStack: UndoEntry[];
  undo: () => Promise<void>;
}

export interface KeypointSlice {
  kpWip: KeypointWip | null;
  /** Visibilidade dada aos próximos pontos marcados (tecla C alterna). */
  kpNextVisibility: KeypointVisibility;
  /** Ponto selecionado da instância selecionada (arrastar, C, etc.). */
  selectedKpIndex: number | null;
  /** Marca o próximo ponto da instância em andamento (cria a instância se preciso). */
  kpPlacePoint: (x: number, y: number) => Promise<void>;
  /** Marca o próximo ponto como ausente (tecla X). */
  kpSkipPoint: () => Promise<void>;
  /** Desfaz o último ponto da instância em andamento; false se não havia. */
  kpUndoPoint: () => boolean;
  kpCancel: () => void;
  /** Fecha a instância agora; pontos que faltam ficam ausentes (tecla F). */
  kpFinish: () => Promise<void>;
  /** Alterna visível/oculto do ponto selecionado, ou dos próximos pontos (tecla C). */
  kpToggleVisibility: () => Promise<void>;
  kpMovePoint: (annId: number, index: number, x: number, y: number) => Promise<void>;
  selectKeypoint: (annId: number, index: number | null) => void;
}

export interface ClassificationSlice {
  classificationResult: ClassificationResult | null;
  /** Número de classe sendo digitado na classificação (> 9 classes). */
  classKeyBuffer: string;
  setClassKeyBuffer: (value: string) => void;
  classifyFrame: (categoryId: number) => Promise<ClassificationResult | null>;
}

export interface SessionUiSlice {
  /** Limpa seleção, desfazer e ID fixado ao abrir uma sessão. */
  resetSessionUi: () => void;
}

export type AnnotationState = FrameSlice &
  EditSlice &
  UndoSlice &
  KeypointSlice &
  ClassificationSlice &
  SessionUiSlice;

/** Assinatura de cada slice: enxerga o estado inteiro, devolve só a sua parte. */
export type Slice<T> = StateCreator<AnnotationState, [], [], T>;

/** O que some ao trocar de frame (seleção e trabalho em andamento são do frame anterior). */
export const FRAME_CHANGE_RESET = {
  classificationResult: null,
  selectedAnnotationId: null,
  selectedKpIndex: null,
  kpWip: null,
} as const;
