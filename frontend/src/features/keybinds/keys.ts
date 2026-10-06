import type { Action, Binds } from "./defaults";

const SPECIAL: Record<string, string> = { " ": "Space", "/": "Slash", ",": "Comma", Esc: "Escape" };

export const sameShortcut = (a: string, b: string): boolean => a.replace("Shift+", "") === b.replace("Shift+", "");

export function keyForEvent(event: KeyboardEvent): string | null {
  if (["Control", "Meta", "Alt", "Shift"].includes(event.key)) return null;
  const key = SPECIAL[event.key] ?? (event.key.length === 1 ? event.key.toUpperCase() : event.key);
  return `${event.ctrlKey || event.metaKey ? "Ctrl+" : ""}${event.altKey ? "Alt+" : ""}${event.shiftKey ? "Shift+" : ""}${key}`;
}

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
  search_class: "all", save: "all", export: "all", settings: "all", undo: "all",
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
