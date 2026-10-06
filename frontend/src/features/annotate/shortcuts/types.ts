import type { AnnotationState } from "../store/types";
import type { Binds } from "../../keybinds/defaults";

/** Trata a tecla se for dela; true = tratada (as próximas regras não rodam). */
export type KeyHandler = (e: KeyboardEvent, s: AnnotationState, binds: Binds) => boolean;
