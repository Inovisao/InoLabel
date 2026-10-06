import type { KeyHandler } from "./types";

/** → / D próximo frame, ← / A frame anterior (descarta o número de classe sendo digitado). */
export const navigationKeys: KeyHandler = (e, s) => {
  switch (e.key) {
    case "ArrowRight":
    case "d":
    case "D":
      e.preventDefault();
      s.setClassKeyBuffer("");
      s.nextFrame();
      return true;
    case "ArrowLeft":
    case "a":
    case "A":
      e.preventDefault();
      s.setClassKeyBuffer("");
      s.prevFrame();
      return true;
  }
  return false;
};
