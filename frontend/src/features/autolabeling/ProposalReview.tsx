import { useEffect, useState } from "react";
import { api } from "../../shared/api/client";
import { useAnnotationStore } from "../annotate/store";
import { pushUndo } from "../annotate/store/undoSlice";
import { useAutolabelingStore } from "./store";
import type { Proposal } from "./types";

export default function ProposalReview({ onReview }: { onReview?: () => void }) {
  const { proposals, drafts, runId, runs, edit, selectedId } = useAutolabelingStore();
  const frame = useAnnotationStore((s) => s.frame);
  const classes = useAnnotationStore((s) => s.classes);
  const visible = useAutolabelingStore((s) => s.visible);
  const batchReview = useAutolabelingStore((s) => s.batchReview);
  const gotoFrame = useAnnotationStore((s) => s.gotoFrame);
  const [busy, setBusy] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);
  const [selectionLoading, setSelectionLoading] = useState(false);
  const { onlyCurrent, offset, total } = useAutolabelingStore();
  const batchActive = batchReview?.runId === runId;
  const batchFrame = batchActive && batchReview.position < batchReview.frameIndices.length
    ? batchReview.frameIndices[batchReview.position] : undefined;
  useEffect(() => {
    if (batchFrame != null && frame?.index !== batchFrame) void gotoFrame(batchFrame);
  }, [batchFrame, runId]);
  useEffect(() => { useAutolabelingStore.setState({ offset: 0, proposals: [] }); }, [frame?.index]);
  const [selected, setSelected] = useState<string[]>([]);
  const [selectedProposals, setSelectedProposals] = useState<Record<string, Proposal>>({});
  const [allCurrentSelected, setAllCurrentSelected] = useState(false);
  useEffect(() => {
    setSelected([]);
    setSelectedProposals({});
    setAllCurrentSelected(false);
  }, [runId, frame?.index]);
  const pending = proposals.filter((p) => p.status === "pending" && (!onlyCurrent || p.frame_index === frame?.index));
  const selectedItems = selected.map((id) => selectedProposals[id] ?? proposals.find((proposal) => proposal.id === id))
    .filter((proposal): proposal is Proposal => proposal !== undefined);
  const currentRun = runs.find((run) => run.id === runId);
  const currentFrameHasPending = frame != null && (currentRun?.pending_frames?.includes(frame.index)
    ?? proposals.some((proposal) => proposal.frame_index === frame.index && proposal.status === "pending"));

  const selectAllCurrentFrame = async (checked: boolean) => {
    if (!checked) {
      setSelected([]);
      setSelectedProposals({});
      setAllCurrentSelected(false);
      return;
    }
    if (!runId || frame == null || selectionLoading || busy) return;
    const requestedRunId = runId;
    const requestedFrameIndex = frame.index;
    setSelectionLoading(true);
    useAutolabelingStore.setState({ onlyCurrent: true, offset: 0, proposals: [] });
    try {
      const items: Proposal[] = [];
      let nextOffset = 0;
      let totalItems = 0;
      do {
        const query = new URLSearchParams({ frame_index: String(frame.index), offset: String(nextOffset), limit: "500" });
        const result = await api.get<{ proposals: Proposal[]; total: number }>(`/autolabeling/runs/${runId}/proposals?${query}`);
        items.push(...result.proposals);
        totalItems = result.total;
        nextOffset += result.proposals.length;
      } while (nextOffset < totalItems);
      if (useAutolabelingStore.getState().runId !== requestedRunId ||
          useAnnotationStore.getState().frame?.index !== requestedFrameIndex) return;
      const currentPending = items.filter((proposal) => proposal.status === "pending");
      setSelected(currentPending.map((proposal) => proposal.id));
      setSelectedProposals(Object.fromEntries(currentPending.map((proposal) => [proposal.id, proposal])));
      setAllCurrentSelected(currentPending.length > 0);
    } catch (e) {
      useAutolabelingStore.setState({ error: (e as Error).message });
    } finally { setSelectionLoading(false); }
  };

  const review = async (items: Proposal[], action: "accept" | "reject" | "undo", advanceBatch = false) => {
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
      setSelectedProposals({});
      setAllCurrentSelected(false);
      if (advanceBatch && batchReview?.runId === runId) {
        useAutolabelingStore.getState().moveBatchReview(batchReview.position + 1);
      }
    } catch (e) {
      useAutolabelingStore.setState({ error: (e as Error).message });
    } finally { setBusy(false); }
  };

  const reviewBatchFrame = async (action: "accept" | "reject") => {
    const currentBatch = useAutolabelingStore.getState().batchReview;
    if (!currentBatch || currentBatch.runId !== runId || batchFrame == null || busy || batchLoading || !runId) return;
    setBatchLoading(true);
    try {
      const items: Proposal[] = [];
      let offset = 0;
      let total = 0;
      do {
        const query = new URLSearchParams({ frame_index: String(batchFrame), offset: String(offset), limit: "500" });
        const result = await api.get<{ proposals: Proposal[]; total: number }>(`/autolabeling/runs/${runId}/proposals?${query}`);
        items.push(...result.proposals);
        total = result.total;
        offset += result.proposals.length;
      } while (offset < total);
      const pendingForFrame = items.filter((proposal) => proposal.status === "pending");
      if (!pendingForFrame.length) {
        useAutolabelingStore.getState().moveBatchReview(currentBatch.position + 1);
        return;
      }
      setBatchLoading(false);
      await review(pendingForFrame, action, true);
    } catch (e) {
      useAutolabelingStore.setState({ error: (e as Error).message });
    } finally { setBatchLoading(false); }
  };

  return <section style={{ display: "grid", gap: 10 }}>
    <h3 style={{ margin: 0 }}>Revisar sugestões</h3>
    {batchActive && batchReview && <section aria-label="Revisão em lote" style={{ display: "grid", gap: 8, padding: 10, border: "1px solid var(--color-border)", borderRadius: 8 }}>
      <strong>Revisão do lote</strong>
      <progress aria-label="Progresso da revisão em lote" value={batchReview.position} max={batchReview.frameIndices.length || 1} style={{ width: "100%" }} />
      {batchFrame == null ? <>
        <span className="text-helper">Revisão concluída · {batchReview.frameIndices.length} imagens processadas</span>
        <button className="btn-secondary" onClick={() => useAutolabelingStore.getState().endBatchReview()}>Fechar revisão</button>
      </> : <>
        <span>Imagem {batchFrame + 1} · {batchReview.position + 1} de {batchReview.frameIndices.length}</span>
        {frame?.index !== batchFrame && <span className="text-helper">Carregando imagem…</span>}
        <button className="btn-primary" disabled={busy || batchLoading || frame?.index !== batchFrame}
          onClick={() => reviewBatchFrame("accept")}>{batchLoading ? "Processando…" : "Aprovar sugestões desta imagem"}</button>
        <button className="btn-secondary" disabled={busy || batchLoading || frame?.index !== batchFrame}
          onClick={() => reviewBatchFrame("reject")}>Reprovar sugestões desta imagem</button>
        <button className="btn-secondary" disabled={busy || batchLoading}
          onClick={() => useAutolabelingStore.getState().endBatchReview()}>Encerrar revisão</button>
      </>}
    </section>}
    <label><input type="checkbox" checked={onlyCurrent} disabled={batchActive} onChange={(e) => useAutolabelingStore.setState({ onlyCurrent: e.target.checked, offset: 0, proposals: [] })} /> Apenas imagem atual</label>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      <label><input type="checkbox" aria-label="Selecionar todas as sugestões da imagem atual"
        checked={allCurrentSelected} disabled={busy || selectionLoading || !currentFrameHasPending}
        onChange={(e) => void selectAllCurrentFrame(e.target.checked)} />
        {selectionLoading ? "Carregando sugestões…" : "Selecionar todas desta imagem"}</label>
      <button className="btn-secondary" disabled={busy || selectionLoading || !selectedItems.length}
        onClick={() => review(selectedItems, "accept")}>Aceitar selecionadas ({selectedItems.length})</button>
      <label><input type="checkbox" checked={visible}
        onChange={(e) => useAutolabelingStore.setState({ visible: e.target.checked })} /> Exibir no canvas</label>
    </div>
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <button className="btn-secondary" disabled={offset === 0 || busy} onClick={() => useAutolabelingStore.setState({ offset: Math.max(0, offset - 100), proposals: [] })}>Anterior</button>
      <span className="text-helper">{total ? offset + 1 : 0}–{Math.min(offset + 100, total)} de {total}</span>
      <button className="btn-secondary" disabled={offset + 100 >= total || busy} onClick={() => useAutolabelingStore.setState({ offset: offset + 100, proposals: [] })}>Próxima</button>
    </div>
    {pending.length === 0 && <p className="text-helper">{total === 0
      ? onlyCurrent
        ? "Esta imagem não tem propostas. Selecione outra imagem ou desative o filtro de imagem atual."
        : "Esta execução não tem propostas para revisar. Consulte as falhas acima, retome a execução ou selecione outra execução com sugestões."
      : "Todas as propostas deste filtro já foram resolvidas."}</p>}
    {pending.map((p) => {
      const draft = drafts[p.id] ?? p;
      return <article key={p.id} style={{ padding: 10, border: `1px solid ${selectedId === p.id ? "#f59e0b" : "var(--color-border)"}`, borderRadius: 6, display: "grid", gap: 8 }}>
        <label><input type="checkbox" checked={selected.includes(p.id)} disabled={busy || selectionLoading || p.frame_index !== frame?.index}
          onChange={(e) => {
            setSelected((items) => e.target.checked ? [...new Set([...items, p.id])] : items.filter((id) => id !== p.id));
            setSelectedProposals((items) => {
              if (e.target.checked) return { ...items, [p.id]: p };
              const { [p.id]: _removed, ...remaining } = items;
              return remaining;
            });
            setAllCurrentSelected(false);
          }} />
          Imagem {p.frame_index + 1} · {p.class_name} · {p.score == null ? "sem score" : (p.score_type && p.score_type !== "detection_confidence" ? `score ${p.score.toFixed(3)}` : `${(p.score * 100).toFixed(1)}%`)}</label>
        {p.prompt && <span className="text-helper">Prompt: {p.prompt}</span>}
        {!batchActive && p.frame_index !== frame?.index && <button className="btn-secondary" disabled={busy} onClick={async () => {
          useAutolabelingStore.setState({ selectedId: p.id });
          await useAnnotationStore.getState().gotoFrame(p.frame_index);
          onReview?.();
        }}>Ver no editor</button>}
        <select aria-label="Classe da sugestão" className="input" value={draft.category_id} disabled={p.frame_index !== frame?.index}
          onChange={(e) => edit(p, { category_id: Number(e.target.value) })}>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 4 }}>
          {(["X", "Y", "Largura", "Altura"] as const).map((name, i) => <label key={name} style={{ fontSize: 11 }}>{name}
            <input type="number" className="input" style={{ width: "100%", padding: 4 }} value={draft.bbox[i]} min={0} disabled={p.frame_index !== frame?.index}
              onChange={(e) => { const bbox = [...draft.bbox] as [number, number, number, number]; bbox[i] = Number(e.target.value); edit(p, { bbox }); }} />
          </label>)}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn-primary" disabled={busy || p.frame_index !== frame?.index} onClick={() => review([p], "accept")}>{drafts[p.id] ? "Editar e aceitar" : "Aceitar"}</button>
          <button className="btn-secondary" disabled={busy || p.frame_index !== frame?.index} onClick={() => review([p], "reject")}>Rejeitar</button>
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
