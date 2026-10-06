import { useEffect, useState } from "react";
import type { Annotation } from "../../../shared/api/types";
import { useAnnotationStore } from "../store";

/** Rastreamento: ID do objeto da caixa selecionada (vazio remove o ID). */
export default function TrackIdField({ ann }: { ann: Annotation }) {
  const { updateAnnotation, fetchNextTrackId } = useAnnotationStore();
  const [text, setText] = useState("");

  useEffect(() => setText(ann.track_id != null ? String(ann.track_id) : ""), [ann.id, ann.track_id]);

  const commit = () => {
    const value = text.trim() === "" ? null : Number(text);
    if (value !== (ann.track_id ?? null)) updateAnnotation(ann.id, { track_id: value });
  };

  return (
    <>
      <label className="text-helper" htmlFor="sel-track">ID do objeto</label>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          id="sel-track"
          className="input text-mono"
          inputMode="numeric"
          value={text}
          onChange={(e) => setText(e.target.value.replace(/\D/g, ""))}
          onBlur={commit}
          onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
          style={{ flex: 1, height: 32, fontSize: 13 }}
        />
        <button
          className="btn-secondary"
          style={{ height: 32, fontSize: 12, whiteSpace: "nowrap" }}
          onClick={async () => {
            const next = await fetchNextTrackId();
            if (next !== null) updateAnnotation(ann.id, { track_id: next });
          }}
        >
          Novo ID
        </button>
      </div>
    </>
  );
}
