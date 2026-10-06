import type { AnnotationState } from "../store/types";
import type { KeyHandler } from "./types";

async function classifyAndAdvance(s: AnnotationState, position: number) {
  const classItem = s.classes[position - 1];
  if (!classItem) return;
  const result = await s.classifyFrame(classItem.id);
  if (result) s.nextFrame();
}

/**
 * Atalho numérico: a classe é a posição na lista (1..N). Até 9 classes a tecla já
 * classifica; acima disso, digita-se o número, que confirma sozinho quando nenhum
 * outro pode começar assim (ex.: 7 de 12) ou com Enter.
 */
function handleDigit(s: AnnotationState, digit: string) {
  const total = s.classes.length;
  if (total <= 9) {
    if (digit !== "0") classifyAndAdvance(s, Number(digit));
    return;
  }
  const typed = s.classKeyBuffer + digit;
  const value = Number(typed);
  if (value < 1 || value > total) {
    s.setClassKeyBuffer("");
    return;
  }
  if (value * 10 > total) {
    s.setClassKeyBuffer("");
    classifyAndAdvance(s, value);
  } else {
    s.setClassKeyBuffer(typed);
  }
}

/** Modo classificação: números, Enter/Backspace/Esc do número digitado e Espaço (pula). */
export const classificationKeys: KeyHandler = (e, s) => {
  if (/^[0-9]$/.test(e.key)) {
    e.preventDefault();
    handleDigit(s, e.key);
    return true;
  }
  if (s.classKeyBuffer) {
    if (e.key === "Enter") {
      e.preventDefault();
      const value = Number(s.classKeyBuffer);
      s.setClassKeyBuffer("");
      classifyAndAdvance(s, value);
      return true;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      s.setClassKeyBuffer(s.classKeyBuffer.slice(0, -1));
      return true;
    }
    if (e.key === "Escape") {
      s.setClassKeyBuffer("");
      return true;
    }
  }
  if (e.key === " ") {
    e.preventDefault();
    s.nextFrame();
    return true;
  }
  return false;
};
