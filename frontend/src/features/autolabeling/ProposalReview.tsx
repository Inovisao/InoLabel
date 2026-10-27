import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { useAnnotationStore } from "../annotate/store";
import { pushUndo } from "../annotate/store/undoSlice";
import { useAutolabelingStore } from "./store";
import type { Proposal } from "./types";

export default function ProposalReview({ onReview }: { onReview?: () => void }) {
  const { proposals, drafts, runId, edit, selectedId } = useAutolabelingStore();
  const frame = useAnnotationStore((s) => s.frame);
  const classes = useAnnotationStore((s) => s.classes);
  const visible = useAutolabelingStore((s) => s.visible);
  const [busy, setBusy] = useState(false);
  const { onlyCurrent, offset, total } = useAutolabelingStore();
  useEffect(() => { useAutolabelingStore.setState({ offset: 0, proposals: [] }); }, [frame?.index]);
  const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => setSelected([]), [runId, offset, frame?.index]);
  const pending = proposals.filter((p) => p.status === "pending" && (!onlyCurrent || p.frame_index === frame?.index));

  const review = async (items: Proposal[], action: "accept" | "reject" | "undo") => {
    if (!runId || busy) return;
    const sessionId = useAutolabelingStore.getState().sessionId;
    setBusy(true);
    try {
      for (const p of items) {
        const result = await api.post<{ proposal: Proposal }>(`/autolabeling/runs/${runId}/${action}`, {
          proposal_id: p.id, ...(action === "accept" ? drafts[p.id] : {}),
        });
        if (useAutolabelingStore.getState().sessionId !== sessionId) return;
        useAutolabelingStore.setState((s) => ({ proposals: s.proposals.map((old) => old.id === p.id ? result.proposal : old) }));
        if (action === "accept") {
          useAnnotationStore.setState((s) => ({ undoStack: pushUndo(s.undoStack, {
            kind: "autolabel", index: p.frame_index, runId, proposalId: p.id,
          }) }));
        }
      }
      await useAnnotationStore.getState().fetchFrame();
      setSelected([]);
    } catch (e) {
      useAutolabelingStore.setState({ error: (e as Error).message });
    } finally { setBusy(false); }
  };

  return <section style={{ display: "grid", gap: 10 }}>
    <h3 style={{ margin: 0 }}>Revisar sugestões</h3>
    <label><input type="checkbox" checked={onlyCurrent} onChange={(e) => useAutolabelingStore.setState({ onlyCurrent: e.target.checked, offset: 0, proposals: [] })} /> Apenas imagem atual</label>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      <button className="btn-secondary" disabled={busy || !pending.some((p) => selected.includes(p.id))}
        onClick={() => review(pending.filter((p) => selected.includes(p.id)), "accept")}>Aceitar selecionadas ({pending.filter((p) => selected.includes(p.id)).length})</button>
      <label><input type="checkbox" checked={visible}
        onChange={(e) => useAutolabelingStore.setState({ visible: e.target.checked })} /> Exibir no canvas</label>
    </div>
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <button className="btn-secondary" disabled={offset === 0 || busy} onClick={() => useAutolabelingStore.setState({ offset: Math.max(0, offset - 100), proposals: [] })}>Anterior</button>
      <span className="text-helper">{total ? offset + 1 : 0}–{Math.min(offset + 100, total)} de {total}</span>
      <button className="btn-secondary" disabled={offset + 100 >= total || busy} onClick={() => useAutolabelingStore.setState({ offset: offset + 100, proposals: [] })}>Próxima</button>
    </div>
    {pending.length === 0 && <p className="text-helper">Nenhuma sugestão pendente neste filtro. Zero detecções não marca a imagem como revisada.</p>}
    {pending.map((p) => {
      const draft = drafts[p.id] ?? p;
      return <article key={p.id} style={{ padding: 10, border: `1px solid ${selectedId === p.id ? "#f59e0b" : "var(--color-border)"}`, borderRadius: 6, display: "grid", gap: 8 }}>
        <label><input type="checkbox" checked={selected.includes(p.id)} onChange={(e) => setSelected((s) => e.target.checked ? [...s, p.id] : s.filter((id) => id !== p.id))} />
          Imagem {p.frame_index + 1} · {p.class_name} · {p.score == null ? "sem score" : `${(p.score * 100).toFixed(1)}%`}</label>
        <button className="btn-secondary" disabled={busy} onClick={async () => {
          useAutolabelingStore.setState({ selectedId: p.id });
          await useAnnotationStore.getState().gotoFrame(p.frame_index);
          onReview?.();
        }}>Ver no editor</button>
        <select aria-label="Classe da sugestão" className="input" value={draft.category_id}
          onChange={(e) => edit(p, { category_id: Number(e.target.value) })}>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 4 }}>
          {(["X", "Y", "Largura", "Altura"] as const).map((name, i) => <label key={name} style={{ fontSize: 11 }}>{name}
            <input type="number" className="input" style={{ width: "100%", padding: 4 }} value={draft.bbox[i]} min={0}
              onChange={(e) => { const bbox = [...draft.bbox] as [number, number, number, number]; bbox[i] = Number(e.target.value); edit(p, { bbox }); }} />
          </label>)}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn-primary" disabled={busy} onClick={() => review([p], "accept")}>{drafts[p.id] ? "Editar e aceitar" : "Aceitar"}</button>
          <button className="btn-secondary" disabled={busy} onClick={() => review([p], "reject")}>Rejeitar</button>
        </div>
      </article>;
    })}
    {proposals.filter((p) => p.status === "accepted" && (!onlyCurrent || p.frame_index === frame?.index)).map((p) =>
      <div key={p.id} style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="text-helper">Imagem {p.frame_index + 1}: aceita</span>
        <button className="btn-secondary" disabled={busy} onClick={() => review([p], "undo")}>Desfazer aceitação</button>
      </div>)}
  </section>;
}
