import type { Annotation, Keypoint } from "../../../shared/api/types";
import { useAnnotationStore } from "../store";

const STATUS: Record<number, string> = { 2: "● visível", 1: "○ oculto", 0: "– ausente" };

/** Keypoint: pontos da instância selecionada com o estado de cada um; clique seleciona. */
export default function KeypointList({ ann, keypoints }: { ann: Annotation; keypoints: Keypoint[] }) {
  const { classes, selectedKpIndex, selectKeypoint } = useAnnotationStore();
  const names = classes.find((c) => c.id === ann.category_id)?.keypoints ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span className="text-helper">Pontos · clique para selecionar · C alterna visível/oculto</span>
      {keypoints.map((p, i) => (
        <button
          key={i}
          className={`nav-item ${selectedKpIndex === i ? "nav-item-active" : ""}`}
          disabled={p[2] === 0}
          onClick={() => selectKeypoint(ann.id, i)}
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "4px 8px",
            fontSize: 12,
            border: "1px solid transparent",
            borderRadius: "var(--radius-sm)",
            cursor: p[2] === 0 ? "default" : "pointer",
            fontFamily: "var(--font-sans)",
            opacity: p[2] === 0 ? 0.55 : 1,
          }}
        >
          <span>{names[i] ?? `#${i + 1}`}</span>
          <span style={{ color: "var(--color-muted)" }}>{STATUS[p[2]]}</span>
        </button>
      ))}
    </div>
  );
}
