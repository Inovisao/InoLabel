import type { KeyHandler } from "./types";

/** OBB: Q/E giram a caixa selecionada 5° (Shift: ajuste fino de 1°). */
export const obbRotationKeys: KeyHandler = (e, s) => {
  if (s.selectedAnnotationId === null || !/^[qe]$/i.test(e.key)) return false;
  e.preventDefault();
  const step = e.shiftKey ? 1 : 5;
  s.rotateSelected({ delta: e.key.toLowerCase() === "q" ? -step : step });
  return true;
};

/** Ferramentas e edição: B desenhar, V selecionar, N frame sem objetos, Del remover, Esc desmarcar. */
export const editKeys: KeyHandler = (e, s) => {
  switch (e.key) {
    case "b":
    case "B":
      s.setTool("box");
      return true;
    case "v":
    case "V":
      s.setTool("select");
      return true;
    case "n":
    case "N":
      e.preventDefault();
      s.toggleReviewed();
      return true;
    case "Delete":
    case "Backspace":
      if (s.selectedAnnotationId !== null) {
        e.preventDefault();
        s.removeAnnotation(s.selectedAnnotationId);
      }
      return true;
    case "Escape":
      s.selectAnnotation(null);
      return true;
  }
  return false;
};
