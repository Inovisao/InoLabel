import { useEffect, useState } from "react";
import { useAnnotationStore } from "../store";

/** Qual ID as próximas caixas recebem: o próximo livre ou um ID fixado. */
export default function TrackIdPanel() {
  const { pinnedTrackId, setPinnedTrackId, fetchNextTrackId, frame } = useAnnotationStore();
  const [nextFree, setNextFree] = useState<number | null>(null);
  const [text, setText] = useState("");

  // Recalcula o próximo livre quando as caixas mudam.
  useEffect(() => {
    fetchNextTrackId().then(setNextFree);
  }, [frame?.index, frame?.annotations, fetchNextTrackId]);

  useEffect(() => {
    setText(pinnedTrackId != null ? String(pinnedTrackId) : "");
  }, [pinnedTrackId]);

  return (
    <>
      <div className="divider" />
      <div className="sidebar-label">ID das próximas caixas</div>
      <div style={{ padding: "0 12px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            className="input text-mono"
            inputMode="numeric"
            placeholder={nextFree != null ? `automático (${nextFree})` : "automático"}
            value={text}
            onChange={(e) => setText(e.target.value.replace(/\D/g, ""))}
            onBlur={() => setPinnedTrackId(text === "" ? null : Number(text))}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
            style={{ flex: 1, height: 32, fontSize: 13 }}
            aria-label="ID fixo para as próximas caixas"
          />
          {pinnedTrackId != null && (
            <button className="btn-secondary" style={{ height: 32, fontSize: 12 }} onClick={() => setPinnedTrackId(null)}>
              Automático
            </button>
          )}
        </div>
        <span className="text-helper">
          {pinnedTrackId != null
            ? `Fixado: toda caixa nova recebe o ID ${pinnedTrackId} (siga o mesmo objeto entre frames).`
            : "Vazio: cada caixa nova recebe o próximo ID livre."}
        </span>
      </div>
    </>
  );
}
