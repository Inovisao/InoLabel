import type { Annotation, OBBGeometry } from "../../../shared/api/types";
import { useSessionStore } from "../../../shared/session/store";
import { useAnnotationStore } from "../store";
import AngleField from "./AngleField";
import KeypointList from "./KeypointList";
import TrackIdField from "./TrackIdField";

/** Edita a anotação selecionada: classe, campo do modo (ID, ângulo, pontos) e remoção. */
export default function SelectionPanel() {
  const { frame, classes, selectedAnnotationId, updateAnnotation, removeAnnotation } = useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);
  const ann = frame?.annotations.find((a) => a.id === selectedAnnotationId);
  if (!ann) return null;
  const isKeypoint = mode === "keypoint";

  return (
    <>
      <div className="divider" />
      <div className="sidebar-label">{isKeypoint ? "Instância selecionada" : "Caixa selecionada"}</div>
      <div style={{ padding: "0 12px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
        <label className="text-helper" htmlFor="sel-class">Classe</label>
        <select
          id="sel-class"
          className="input"
          value={ann.category_id}
          onChange={(e) => updateAnnotation(ann.id, { category_id: Number(e.target.value) })}
          style={{ height: 32, fontSize: 13 }}
        >
          {classes.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        {mode === "obb" && ann.obb && <AngleField ann={ann as Annotation & { obb: OBBGeometry }} />}
        {mode === "tracking" && <TrackIdField ann={ann} />}
        {isKeypoint && ann.keypoints && <KeypointList ann={ann} keypoints={ann.keypoints} />}

        <button
          className="btn-secondary"
          style={{ height: 32, fontSize: 12, color: "var(--color-danger)" }}
          onClick={() => removeAnnotation(ann.id)}
        >
          {isKeypoint ? "Remover instância (Del)" : "Remover caixa (Del)"}
        </button>
      </div>
    </>
  );
}
