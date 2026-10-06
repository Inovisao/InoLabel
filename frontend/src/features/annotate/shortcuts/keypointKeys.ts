import type { KeyHandler } from "./types";

/**
 * Modo keypoint (atalhos da 1.0.0): X pula o ponto, C alterna visível/oculto,
 * F fecha a instância, Backspace desfaz o ponto, Esc cancela a instância em andamento.
 */
export const keypointKeys: KeyHandler = (e, s) => {
  switch (e.key.toLowerCase()) {
    case "x":
      e.preventDefault();
      s.kpSkipPoint();
      return true;
    case "c":
      e.preventDefault();
      s.kpToggleVisibility();
      return true;
    case "f":
      e.preventDefault();
      s.kpFinish();
      return true;
    case "backspace":
      e.preventDefault();
      s.kpUndoPoint();
      return true;
    case "escape":
      if (!s.kpWip) return false;   // sem instância em andamento, Esc desmarca a seleção
      s.kpCancel();
      return true;
  }
  return false;
};
