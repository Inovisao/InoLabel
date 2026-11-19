import type { Annotation, ClassItem, TaskMode } from "../../../shared/api/types";

const FALLBACK_COLOR = "#4F46E5";

/**
 * Cores dos IDs no rastreamento. Precisam ser cores reais: o canvas não entende
 * variáveis de CSS (var(--…)) e desenhava essas caixas em preto.
 */
export const TRACK_COLORS = [
  "#3B82F6", "#22C55E", "#F59E0B", "#EF4444", "#A855F7", "#14B8A6",
  "#EC4899", "#84CC16", "#06B6D4", "#F97316",
];

function colorForTrack(trackId: number) {
  return TRACK_COLORS[Math.abs(trackId) % TRACK_COLORS.length];
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
