import type { AnnotationState } from "../store/types";

/** Trata a tecla se for dela; true = tratada (as próximas regras não rodam). */
export type KeyHandler = (e: KeyboardEvent, s: AnnotationState) => boolean;
