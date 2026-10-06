import type { KeyHandler } from "./types";
import { matches } from "../../keybinds/keys";

/** → / D próximo frame, ← / A frame anterior (descarta o número de classe sendo digitado). */
export const navigationKeys: KeyHandler = (e, s, binds) => {
  if (matches(e, binds, "next_frame")) {
    e.preventDefault();
    s.setClassKeyBuffer("");
    s.nextFrame();
    return true;
  }
  if (matches(e, binds, "prev_frame")) {
    e.preventDefault();
    s.setClassKeyBuffer("");
    s.prevFrame();
    return true;
  }
  return false;
};
