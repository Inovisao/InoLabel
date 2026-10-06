/**
 * Estado da tela de anotação. Um store só (os componentes leem qualquer parte),
 * montado a partir de slices por responsabilidade.
 */
import { create } from "zustand";
import { createClassificationSlice } from "./classificationSlice";
import { createEditSlice } from "./editSlice";
import { createFrameSlice } from "./frameSlice";
import { createKeypointSlice } from "./keypointSlice";
import type { AnnotationState } from "./types";
import { createUndoSlice } from "./undoSlice";

export type { KeypointVisibility, KeypointWip, Tool } from "./types";

export const useAnnotationStore = create<AnnotationState>()((...a) => {
  const [set] = a;
  return {
    ...createFrameSlice(...a),
    ...createEditSlice(...a),
    ...createUndoSlice(...a),
    ...createKeypointSlice(...a),
    ...createClassificationSlice(...a),

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
  };
});
