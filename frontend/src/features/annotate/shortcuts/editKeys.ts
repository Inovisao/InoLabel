import type { KeyHandler } from "./types";
import { matches } from "../../keybinds/keys";

/** OBB: Q/E giram a caixa selecionada 5° (Shift: ajuste fino de 1°). */
export const obbRotationKeys: KeyHandler = (e, s, binds) => {
  if (s.selectedAnnotationId === null) return false;
  const left = matches(e, binds, "rotate_left");
  if (!left && !matches(e, binds, "rotate_right")) return false;
  e.preventDefault();
  const step = e.shiftKey ? 1 : 5;
  s.rotateSelected({ delta: left ? -step : step });
  return true;
};

/** Ferramentas e edição: B desenhar, V selecionar, N frame sem objetos, Del remover, Esc desmarcar. */
export const editKeys: KeyHandler = (e, s, binds) => {
  if (matches(e, binds, "tool_box")) { s.setTool("box"); return true; }
  if (matches(e, binds, "tool_select")) { s.setTool("select"); return true; }
  if (matches(e, binds, "mark_negative")) { e.preventDefault(); s.toggleReviewed(); return true; }
  if (matches(e, binds, "delete_annotation")) {
    if (s.selectedAnnotationId !== null) {
      e.preventDefault();
      s.removeAnnotation(s.selectedAnnotationId);
    }
    return true;
  }
  if (matches(e, binds, "deselect")) { s.selectAnnotation(null); return true; }
  return false;
};
