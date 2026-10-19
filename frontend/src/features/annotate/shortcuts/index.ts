import type { TaskMode } from "../../../shared/api/types";
import { classificationKeys } from "./classificationKeys";
import { editKeys, obbRotationKeys, selectionKeys, viewKeys } from "./editKeys";
import { keypointKeys } from "./keypointKeys";
import { navigationKeys } from "./navigationKeys";
import type { KeyHandler } from "./types";

/** Regras de tecla do modo, em ordem de prioridade; a navegação entre frames vem por último. */
export function handlersFor(mode: TaskMode | null): KeyHandler[] {
  const byMode: KeyHandler[] =
    mode === "classification"
      ? [classificationKeys]
      : mode === "keypoint"
        ? [keypointKeys, selectionKeys, editKeys]
        : mode === "obb"
          ? [obbRotationKeys, selectionKeys, editKeys]
          : [selectionKeys, editKeys];
  return [viewKeys, ...byMode, navigationKeys];
}
