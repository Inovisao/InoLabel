import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { api } from "../../shared/api/client";
import { useSessionStore } from "../../shared/session/store";
import { useAnnotationStore } from "../annotate/store";
import { useAutolabelingStore } from "./store";
import ProposalReview from "./ProposalReview";
import RuntimeDiagnostics from "./RuntimeDiagnostics";
import type { LabelingRun, ModelConfig } from "./types";

export default function AutolabelingPanel({ workspace = false, onReview, onClose }: {
  workspace?: boolean; onReview?: () => void; onClose?: () => void;
}) {
  const { sessionId, mode } = useSessionStore();
  const frame = useAnnotationStore((s) => s.frame);
  const classes = useAnnotationStore((s) => s.classes);
  const { runs, runId, error, selectRun } = useAutolabelingStore();
  const { config, modelClasses, inspectedPath } = useAutolabelingStore();
  const setConfig: Dispatch<SetStateAction<ModelConfig>> = (update) => useAutolabelingStore.setState((s) => ({
    config: typeof update === "function" ? update(s.config) : update, configurationLoaded: true,
  }));
  const setModelClasses = (modelClasses: string[]) => useAutolabelingStore.setState({ modelClasses });
  const setInspectedPath = (inspectedPath: string) => useAutolabelingStore.setState({ inspectedPath });
  const { scope, indices } = useAutolabelingStore();
  const setScope = (scope: string) => useAutolabelingStore.setState({ scope });
  const setIndices = (indices: string) => useAutolabelingStore.setState({ indices });
  const [busy, setBusy] = useState(false);
  const selectedRun = runs.find((r) => r.id === runId);

  useEffect(() => {
    let cancelled = false;
    if (mode === "detection" && !useAutolabelingStore.getState().configurationLoaded) api.get<ModelConfig>("/autolabeling/config").then((c) => {
      if (!cancelled && !useAutolabelingStore.getState().configurationLoaded) useAutolabelingStore.setState((s) => ({ config: { ...s.config, ...c }, configurationLoaded: true }));
    }).catch((e) => { if (!cancelled) useAutolabelingStore.setState({ error: e.message }); });
    return () => { cancelled = true; };
  }, [sessionId, mode]);

  const perform = async (work: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); useAutolabelingStore.setState({ error: null });
    try { await work(); } catch (e) { if (useSessionStore.getState().sessionId === sessionId) useAutolabelingStore.setState({ error: (e as Error).message }); }
    finally { setBusy(false); }
  };
  const inspect = () => perform(async () => {
    const result = await api.post<{ classes: string[]; model_path: string }>("/autolabeling/models/inspect", config);
    if (useSessionStore.getState().sessionId !== sessionId) return;
    setModelClasses(result.classes); setInspectedPath(result.model_path);
    setConfig((c) => ({ ...c, model_path: result.model_path, class_mapping: Object.fromEntries(
      result.classes.map((name) => [name, c.class_mapping[name] ?? (classes.some((cl) => cl.name === name) ? name : null)]),
    ) }));
  });
  const run = () => perform(async () => {
    const frame_indices = scope === "all" ? null : scope === "current" ? [frame!.index] : indices.split(",").map((s) => Number(s.trim()) - 1);
    if (frame_indices && (!frame_indices.length || frame_indices.some((i) => !Number.isInteger(i) || i < 0))) throw new Error("Informe números de imagens separados por vírgula, começando em 1.");
    const result = await api.post<LabelingRun>("/autolabeling/runs", { session_id: sessionId, config, frame_indices });
    if (useSessionStore.getState().sessionId !== sessionId) return;
    useAutolabelingStore.setState((s) => ({ runs: [result, ...s.runs], runId: result.id, proposals: [], drafts: {} }));
  });

  return <aside style={{ width: workspace ? "100%" : 350, minWidth: workspace ? undefined : 300,
    maxWidth: workspace ? 1000 : "40vw", overflowY: "auto", padding: workspace ? 28 : 16,
    borderLeft: "1px solid var(--color-border)", background: "var(--color-panel)", display: "grid", alignContent: "start", gap: 16 }}>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Autolabeling</h2>
      {onClose && <button className="btn-secondary" onClick={onClose}>Fechar</button>}
      {workspace && <button className="btn-secondary" onClick={onReview}>Voltar à anotação</button>}
    </div>
    {mode !== "detection" ? <p>O fluxo de sugestões de caixas está disponível em projetos de detecção. Os demais modos continuam com anotação manual.</p> : <>
      <div style={{ display: "grid", gap: 8 }}>
        <strong>Modelo treinado · YOLO local</strong>
        <RuntimeDiagnostics />
        <span className="text-helper">Modelos fundacionais: integração prevista; ainda indisponível.</span>
        <p className="text-helper">As sugestões só entram nas anotações e exportações após sua aceitação.</p>
        <label>Checkpoint .pt
          <input className="input" style={{ width: "100%" }} value={config.model_path}
            onChange={(e) => { setConfig((c) => ({ ...c, model_path: e.target.value })); setModelClasses([]); setInspectedPath(""); }} />
        </label>
        <button className="btn-secondary" disabled={busy} onClick={() => perform(async () => {
          const result = await api.get<{ path: string }>("/browse/file");
          if (result.path) { setConfig((c) => ({ ...c, model_path: result.path })); setInspectedPath(""); setModelClasses([]); }
        })}>Selecionar arquivo</button>
        <span className="text-helper">Carregue apenas pesos de origem confiável.</span>
        <button className="btn-secondary" disabled={busy || !config.model_path} onClick={inspect}>{busy ? "Aguarde…" : "Inspecionar modelo"}</button>
        {modelClasses.map((name) => <label key={name} style={{ display: "grid", gap: 4 }}>{name} →
          <select className="input" value={config.class_mapping[name] ?? ""} onChange={(e) => setConfig((c) => ({ ...c, class_mapping: { ...c.class_mapping, [name]: e.target.value || null } }))}>
            <option value="">Ignorar classe</option>
            {classes.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
        </label>)}
        <label>Confiança mínima
          <input className="input" type="number" min={0} max={1} step={0.05} value={config.confidence}
            onChange={(e) => setConfig((c) => ({ ...c, confidence: Number(e.target.value) }))} />
        </label>
        <label>Processar
          <select className="input" style={{ width: "100%" }} value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="current">Imagem atual</option><option value="selected">Imagens selecionadas</option><option value="all">Todo o dataset</option>
          </select>
        </label>
        {scope === "selected" && <label>Números das imagens (ex.: 1, 3, 5)
          <input className="input" value={indices} onChange={(e) => setIndices(e.target.value)} />
        </label>}
        <button className="btn-primary" disabled={busy || !frame || inspectedPath !== config.model_path || !Object.values(config.class_mapping).some(Boolean)} onClick={run}>
          {scope === "current" ? "Gerar sugestões" : "Executar em lote"}
        </button>
      </div>
      {error && <div role="alert" className="alert alert-error">{error}<button className="btn-secondary" onClick={() => useAutolabelingStore.setState({ error: null })}>Fechar aviso</button></div>}
      <section style={{ display: "grid", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Execuções</h3>
        {!runs.length && <span className="text-helper">Nenhuma execução neste projeto.</span>}
        {runs.length > 0 && <select aria-label="Execução selecionada" className="input" value={runId ?? ""} onChange={(e) => selectRun(e.target.value)}>
          {runs.map((r) => <option key={r.id} value={r.id}>{new Date(r.created_at).toLocaleString()} · {r.status}</option>)}
        </select>}
        {selectedRun && <>
          <span>{selectedRun.processed}/{selectedRun.total} imagens · {selectedRun.pending} pendentes · {selectedRun.accepted} aceitas</span>
          <progress aria-label="Progresso da execução" value={selectedRun.processed} max={selectedRun.total} style={{ width: "100%" }} />
          <span className="text-helper">{selectedRun.config.model_path}</span>
          {selectedRun.error && <p role="alert">{selectedRun.error}</p>}
          {selectedRun.failed > 0 && <details><summary>{selectedRun.failed} imagens com falha</summary>
            {Object.entries(selectedRun.outcomes).filter(([, o]) => o.status === "failed").map(([i, o]) => <p key={i}>Imagem {Number(i) + 1}: {o.error}</p>)}
          </details>}
          {(["queued", "running"].includes(selectedRun.status)) && <button className="btn-secondary" onClick={() => perform(async () => { await api.post(`/autolabeling/runs/${runId}/cancel`); })}>Cancelar execução</button>}
          {(["cancelled", "interrupted", "failed", "partially_failed"].includes(selectedRun.status)) && <button className="btn-secondary" onClick={() => perform(async () => { await api.post(`/autolabeling/runs/${runId}/resume`); })}>Retomar execução</button>}
        </>}
      </section>
      {runId && <ProposalReview onReview={onReview} />}
    </>}
  </aside>;
}
