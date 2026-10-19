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

const NUDGES = [
  ["nudge_left", -1, 0],
  ["nudge_right", 1, 0],
  ["nudge_up", 0, -1],
  ["nudge_down", 0, 1],
] as const;

/** Seleção em bloco: selecionar tudo, copiar, colar e mover com Alt+setas (Shift: 10 px). */
export const selectionKeys: KeyHandler = (e, s, binds) => {
  if (matches(e, binds, "select_all")) { e.preventDefault(); s.selectAll(); return true; }
  if (matches(e, binds, "copy")) {
    if (s.selectedIds.length) { e.preventDefault(); s.copySelection(); }
    return true;
  }
  if (matches(e, binds, "paste")) {
    if (s.clipboard?.length) { e.preventDefault(); s.pasteClipboard(); }
    return true;
  }
  for (const [action, x, y] of NUDGES) {
    if (!matches(e, binds, action)) continue;
    // Alt+seta também é "voltar página" no navegador: sempre bloqueado aqui.
    e.preventDefault();
    const step = e.shiftKey ? 10 : 1;
    if (s.selectedIds.length) s.moveSelection(x * step, y * step);
    return true;
  }
  return false;
};

/** Ferramentas e edição: B desenhar, V selecionar, N frame sem objetos, Del remover, Esc desmarcar. */
export const editKeys: KeyHandler = (e, s, binds) => {
  if (matches(e, binds, "tool_box")) { s.setTool("box"); return true; }
  if (matches(e, binds, "tool_select")) { s.setTool("select"); return true; }
  if (matches(e, binds, "mark_negative")) { e.preventDefault(); s.toggleReviewed(); return true; }
  if (matches(e, binds, "delete_annotation")) {
    if (s.selectedIds.length > 1) {
      e.preventDefault();
      s.removeSelection();
    } else if (s.selectedAnnotationId !== null) {
      e.preventDefault();
      s.removeAnnotation(s.selectedAnnotationId);
    }
    return true;
  }
  if (matches(e, binds, "deselect")) { s.selectAnnotation(null); return true; }
  return false;
};
