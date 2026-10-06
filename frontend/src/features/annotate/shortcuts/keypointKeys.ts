import type { KeyHandler } from "./types";
import { matches } from "../../keybinds/keys";

/**
 * Modo keypoint (atalhos da 1.0.0): X pula o ponto, C alterna visível/oculto,
 * F fecha a instância, Backspace desfaz o ponto, Esc cancela a instância em andamento.
 */
export const keypointKeys: KeyHandler = (e, s, binds) => {
  if (matches(e, binds, "kp_skip")) { e.preventDefault(); s.kpSkipPoint(); return true; }
  if (matches(e, binds, "kp_visibility")) { e.preventDefault(); s.kpToggleVisibility(); return true; }
  if (matches(e, binds, "kp_finish")) { e.preventDefault(); s.kpFinish(); return true; }
  if (matches(e, binds, "kp_undo")) { e.preventDefault(); s.kpUndoPoint(); return true; }
  if (matches(e, binds, "kp_cancel")) {
    if (!s.kpWip) return false;
    s.kpCancel();
    return true;
  }
  return false;
};
