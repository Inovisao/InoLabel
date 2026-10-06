import type { TaskMode } from "../../../shared/api/types";
import { classificationKeys } from "./classificationKeys";
import { editKeys, obbRotationKeys } from "./editKeys";
import { keypointKeys } from "./keypointKeys";
import { navigationKeys } from "./navigationKeys";
import type { KeyHandler } from "./types";

/** Regras de tecla do modo, em ordem de prioridade; a navegação entre frames vem por último. */
export function handlersFor(mode: TaskMode | null): KeyHandler[] {
  const byMode: KeyHandler[] =
    mode === "classification"
      ? [classificationKeys]
      : mode === "keypoint"
        ? [keypointKeys, editKeys]
        : mode === "obb"
          ? [obbRotationKeys, editKeys]
          : [editKeys];
  return [...byMode, navigationKeys];
}
