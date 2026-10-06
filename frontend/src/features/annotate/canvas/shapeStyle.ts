import type { Annotation, ClassItem, TaskMode } from "../../../shared/api/types";

const FALLBACK_COLOR = "#4F46E5";

const TRACK_COLOR_VARS = [
  "--color-icon-track-fg",
  "--color-icon-detect-fg",
  "--color-icon-obb-fg",
  "--color-icon-class-fg",
  "--color-primary",
  "--color-danger",
];

function colorForTrack(trackId: number) {
  return `var(${TRACK_COLOR_VARS[Math.abs(trackId) % TRACK_COLOR_VARS.length]})`;
}

/** Cor e rótulo da forma: no rastreamento a cor segue o ID; nos outros modos, a classe. */
export function shapeStyle(ann: Annotation, cls: ClassItem | undefined, mode: TaskMode | null) {
  const hasTrack = mode === "tracking" && ann.track_id != null;
  const name = cls?.name ?? `#${ann.category_id}`;
  return {
    color: hasTrack ? colorForTrack(ann.track_id as number) : cls?.color ?? FALLBACK_COLOR,
    label: hasTrack ? `ID ${ann.track_id} | ${name}` : mode === "tracking" ? `sem ID | ${name}` : name,
  };
}

export const DEFAULT_DRAW_COLOR = FALLBACK_COLOR;
