import type { Action, Binds } from "./defaults";

const SPECIAL: Record<string, string> = { " ": "Space", "/": "Slash", ",": "Comma", Esc: "Escape" };

export const sameShortcut = (a: string, b: string): boolean => a.replace("Shift+", "") === b.replace("Shift+", "");

type Modifiers = Pick<KeyboardEvent, "ctrlKey" | "metaKey" | "altKey" | "shiftKey">;

const modifiers = (e: Modifiers) => `${e.ctrlKey || e.metaKey ? "Ctrl+" : ""}${e.altKey ? "Alt+" : ""}${e.shiftKey ? "Shift+" : ""}`;

export function keyForEvent(event: KeyboardEvent): string | null {
  if (["Control", "Meta", "Alt", "Shift"].includes(event.key)) return null;
  const key = SPECIAL[event.key] ?? (event.key.length === 1 ? event.key.toUpperCase() : event.key);
  return `${modifiers(event)}${key}`;
}

/** Tecla sem modificadores (o keyup de "Ctrl+H" pode chegar já sem o Ctrl). */
export const baseKey = (key: string): string => key.replace(/^(Ctrl\+|Alt\+|Shift\+)+(?=.)/, "");

/** Ações acionadas pelo mouse: a roda (zoom) e o arraste (mover a imagem). */
export const MOUSE_ACTIONS: Partial<Record<Action, "wheel" | "drag">> = { zoom_wheel: "wheel", pan_drag: "drag" };

/** Roda do mouse com modificadores, ex.: "Ctrl+Wheel". */
export const wheelForEvent = (event: Modifiers): string => `${modifiers(event)}Wheel`;

const BUTTONS = ["Left", "Middle", "Right"];

/** Arraste com um botão do mouse, ex.: "MiddleDrag", "Alt+LeftDrag". */
export function dragForEvent(event: Modifiers & { button: number }): string | null {
  const button = BUTTONS[event.button];
  return button ? `${modifiers(event)}${button}Drag` : null;
}

export const isMouseShortcut = (key: string): boolean => /(Wheel|Drag)$/.test(key);

/** Arraste com o botão esquerdo sem modificador é o gesto de desenhar caixas. */
export const PLAIN_LEFT_DRAG = "LeftDrag";

const LABELS: Record<string, string> = {
  Wheel: "Roda", LeftDrag: "Botão esquerdo", MiddleDrag: "Botão do meio", RightDrag: "Botão direito",
};

/** Texto do atalho na tela: os gestos de mouse em português, as teclas como estão. */
export function shortcutLabel(key: string): string {
  const mods = key.match(/^(Ctrl\+|Alt\+|Shift\+)*/)?.[0] ?? "";
  const rest = key.slice(mods.length);
  return LABELS[rest] ? `${mods}${LABELS[rest]}` : key;
}

export const matchesGesture = (gesture: string | null, binds: Binds, action: Action): boolean =>
  gesture !== null && binds[action].includes(gesture);

export function matches(event: KeyboardEvent, binds: Binds, action: Action): boolean {
  const key = keyForEvent(event);
  if (!key) return false;
  if (binds[action].includes(key)) return true;
  // Shift refines OBB rotation and must not disable its shortcut.
  return event.shiftKey && binds[action].includes(key.replace("Shift+", ""));
}

const CONTEXT: Record<Action, string> = {
  next_frame: "all", prev_frame: "all", tool_box: "edit", tool_select: "edit",
  mark_negative: "edit", delete_annotation: "edit", deselect: "edit", rotate_left: "obb",
  rotate_right: "obb", kp_skip: "kp", kp_visibility: "kp", kp_finish: "kp",
  kp_undo: "kp", kp_cancel: "kp", classification_skip: "classification",
  search_class: "all", save: "all", export: "all", settings: "all", undo: "all", redo: "all",
  zoom_wheel: "all", zoom_fit: "all", pan_drag: "all", pan_hold: "all",
  copy: "edit", paste: "edit", select_all: "edit",
  nudge_left: "edit", nudge_right: "edit", nudge_up: "edit", nudge_down: "edit",
  rotate_view_cw: "all", rotate_view_ccw: "all",
};

export function conflict(binds: Binds, action: Action, key: string): Action | null {
  for (const other of Object.keys(binds) as Action[]) {
    if (other === action || !binds[other].some((bound) => sameShortcut(bound, key))) continue;
    const a = CONTEXT[action], b = CONTEXT[other];
    if (a === "all" || b === "all" || a === b || a === "edit" && b === "obb" || a === "obb" && b === "edit" || a === "edit" && b === "kp" || a === "kp" && b === "edit") {
      // Esc and Backspace have deliberate priority in an active keypoint instance.
      if (["kp_cancel", "deselect"].includes(action) && ["kp_cancel", "deselect"].includes(other)) continue;
      if (["kp_undo", "delete_annotation"].includes(action) && ["kp_undo", "delete_annotation"].includes(other)) continue;
      return other;
    }
  }
  return null;
}

export function reserved(action: Action, key: string): boolean {
  return ["all", "classification"].includes(CONTEXT[action]) &&
    ("0123456789".includes(key) && key.length === 1 || ["Enter", "Backspace", "Escape"].includes(key));
}
