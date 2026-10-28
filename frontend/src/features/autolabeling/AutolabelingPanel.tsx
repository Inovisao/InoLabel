import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { api } from "../../shared/api/client";
import { useSessionStore } from "../../shared/session/store";
import { useAnnotationStore } from "../annotate/store";
import { useAutolabelingStore } from "./store";
import ProposalReview from "./ProposalReview";
import ModelSourceSelector from "./model-config/ModelSourceSelector";
import ImportedModelSection from "./model-config/ImportedModelSection";
import FoundationModelSection from "./model-config/FoundationModelSection";
import BatchImageSelectionDialog from "./BatchImageSelectionDialog";
import { inputErrors } from "./model-config/schema";
import "./model-config/styles.css";
import type { CatalogModel, LabelingRun, ModelConfig } from "./types";

export default function AutolabelingPanel({ workspace = false, onReview, onClose }: {
  workspace?: boolean; onReview?: () => void; onClose?: () => void;
}) {
  const { sessionId, mode } = useSessionStore();
  const frame = useAnnotationStore((s) => s.frame);
  const classes = useAnnotationStore((s) => s.classes);
  const { runs, runId, error, selectRun } = useAutolabelingStore();
  const { config, modelClasses, inspectedPath, catalog, chooseModel } = useAutolabelingStore();
  const setConfig: Dispatch<SetStateAction<ModelConfig>> = (update) => useAutolabelingStore.setState((s) => {
    const next = typeof update === "function" ? update(s.config) : update;
    return { config: next, configurationLoaded: true,
      ...(next.model_path !== s.config.model_path ? { inspectedPath: "", modelClasses: [] } : {}) };
  });
  const selectedModel = catalog.find((model) => model.id === (config.model_id ?? config.adapter));
  const source = selectedModel?.source ?? "imported";
  const foundationModels = catalog.filter((model) => model.source === "catalog");
  const validConfig = source === "imported"
    ? !!config.model_path && inspectedPath === config.model_path && Object.values(config.class_mapping).some(Boolean)
    : selectedModel?.availability === "configured" && inputErrors(selectedModel.input_schema, config.parameters ?? {}).length === 0;
  const { scope } = useAutolabelingStore();
  const setScope = (scope: string) => useAutolabelingStore.setState({ scope });
  const [busy, setBusy] = useState(false);
  const [imagePickerOpen, setImagePickerOpen] = useState(false);
  const [selectedFrameIndices, setSelectedFrameIndices] = useState<number[]>([]);
  const selectedRun = runs.find((r) => r.id === runId);

  useEffect(() => {
    let cancelled = false;
    api.get<CatalogModel[]>("/autolabeling/models?task=detect_boxes").then((models) => {
      if (!cancelled) useAutolabelingStore.setState({ catalog: models });
    }).catch((e) => { if (!cancelled) useAutolabelingStore.setState({ error: e.message }); });
    return () => { cancelled = true; };
  }, [sessionId]);

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
    useAutolabelingStore.setState((s) => ({ modelClasses: result.classes, inspectedPath: result.model_path,
      config: { ...s.config, model_path: result.model_path, class_mapping: Object.fromEntries(
        result.classes.map((name) => [name, s.config.class_mapping[name] ?? (classes.some((cl) => cl.name === name) ? name : null)]),
      ) },
    }));
  });
  const run = (currentOnly = false) => perform(async () => {
    const frame_indices = currentOnly || scope === "current" ? [frame!.index]
      : scope === "all" ? null : selectedFrameIndices;
    if (scope === "selected" && !currentOnly && !selectedFrameIndices.length) throw new Error("Selecione ao menos uma imagem para o lote.");
    if (frame_indices && (!frame_indices.length || frame_indices.some((i) => !Number.isInteger(i) || i < 0))) throw new Error("Selecione imagens válidas para processar.");
    if (selectedModel && source === "catalog") {
      const errors = inputErrors(selectedModel.input_schema, config.parameters ?? {});
      if (errors.length) throw new Error(errors.join(" "));
    }
    const result = await api.post<LabelingRun>("/autolabeling/runs", { session_id: sessionId, config, frame_indices });
    if (useSessionStore.getState().sessionId !== sessionId) return;
    useAutolabelingStore.setState((s) => ({ runs: [result, ...s.runs], runId: result.id, proposals: [], drafts: {} }));
  });
  const beginBatchReview = () => {
    if (!selectedRun || !selectedRun.pending_frames?.length || ["queued", "running"].includes(selectedRun.status)) return;
    useAutolabelingStore.getState().startBatchReview(selectedRun.id, selectedRun.pending_frames);
    onReview?.();
  };

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
        <ModelSourceSelector value={source} disabled={busy || !catalog.length} onChange={(target) => {
          const model = catalog.find((entry) => entry.source === target);
          if (model && target !== source) chooseModel(model);
        }} />
        <p className="text-helper">As sugestões só entram nas anotações e exportações após sua aceitação.</p>
        {source === "imported" ? <ImportedModelSection config={config} setConfig={setConfig} modelClasses={modelClasses}
          classes={classes} busy={busy} onInspect={inspect} onBrowse={() => perform(async () => {
            const result = await api.get<{ path: string }>("/browse/file");
            if (result.path) setConfig((c) => ({ ...c, model_path: result.path }));
          })} /> : <FoundationModelSection models={foundationModels} model={selectedModel} config={config}
            setConfig={setConfig} classes={classes} busy={busy} />}
        {source === "catalog" && <button className="btn-secondary" disabled={busy || !frame || !validConfig}
          onClick={() => run(true)}>Testar na imagem atual</button>}
        <label>Processar
          <select className="input" style={{ width: "100%" }} value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="current">Imagem atual</option><option value="selected">Imagens selecionadas</option><option value="all">Todo o dataset</option>
          </select>
        </label>
        {scope === "selected" && <button className="btn-secondary" disabled={busy} onClick={() => setImagePickerOpen(true)}>
          {selectedFrameIndices.length ? `Alterar seleção · ${selectedFrameIndices.length} imagens` : "Selecionar imagens…"}
        </button>}
        <button className="btn-primary" disabled={busy || !frame || !validConfig || (scope === "selected" && selectedFrameIndices.length === 0)} onClick={() => run()}>
          {scope === "current" ? "Gerar sugestões" : "Executar em lote"}
        </button>
      </div>
      {error && <div role="alert" className="alert alert-error">{error}<button className="btn-secondary" onClick={() => useAutolabelingStore.setState({ error: null })}>Fechar aviso</button></div>}
      <section style={{ display: "grid", gap: 8 }}>
        <h3 style={{ margin: 0 }}>Execuções</h3>
        {!runs.length && <span className="text-helper">Nenhuma execução neste projeto.</span>}
        {runs.length > 0 && <select aria-label="Execução selecionada" className="input" value={runId ?? ""} onChange={(e) => selectRun(e.target.value)}>
          {runs.map((r) => <option key={r.id} value={r.id}>{new Date(r.created_at).toLocaleString()} · {r.status} · {r.pending} pendentes</option>)}
        </select>}
        {selectedRun && <>
          <span>{selectedRun.processed}/{selectedRun.total} imagens · {selectedRun.pending} pendentes · {selectedRun.accepted} aceitas</span>
          <progress aria-label="Progresso da execução" value={selectedRun.processed} max={selectedRun.total} style={{ width: "100%" }} />
          <span className="text-helper">{selectedRun.model_definition?.name ?? selectedRun.config.model_path}</span>
          {Boolean(selectedRun.pending_frames?.length) && <button className="btn-primary" disabled={["queued", "running"].includes(selectedRun.status)} onClick={beginBatchReview}>
            Revisar lote · {selectedRun.pending_frames!.length} imagens pendentes
          </button>}
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
    <BatchImageSelectionDialog open={imagePickerOpen} selectedIndices={selectedFrameIndices}
      onApply={setSelectedFrameIndices} onClose={() => setImagePickerOpen(false)} />
  </aside>;
}
