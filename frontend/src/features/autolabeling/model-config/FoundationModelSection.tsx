import { useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { ClassItem } from "../../../shared/api/types";
import type { CatalogModel, ModelConfig } from "../types";
import { useAutolabelingStore } from "../store";
import ModelConfigForm from "./ModelConfigForm";
import ModelSetupDialog from "./ModelSetupDialog";
import { inputErrors, schemaDefaults } from "./schema";
import { api } from "../../../shared/api/client";

export default function FoundationModelSection({ models, model, config, setConfig, classes, busy }: {
  models: CatalogModel[]; model?: CatalogModel; config: ModelConfig;
  setConfig: Dispatch<SetStateAction<ModelConfig>>; classes: ClassItem[]; busy: boolean;
}) {
  const [setupOpen, setSetupOpen] = useState(false);
  const [download, setDownload] = useState<{ id: string; status: string; progress: string; completed: number; total: number } | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  useEffect(() => {
    if (!download || !["queued", "running"].includes(download.status)) return;
    const timer = window.setInterval(() => {
      api.get<typeof download & { error?: string }>(`/autolabeling/ollama/downloads/${download.id}`).then((result) => {
        setDownload(result);
        if (result.status === "succeeded") api.get<CatalogModel[]>("/autolabeling/models?task=detect_boxes").then((catalog) =>
          useAutolabelingStore.setState({ catalog }));
        if (result.status === "failed") setDownloadError("Falha ao baixar o modelo pelo Ollama. Verifique a conexão e o espaço disponível.");
      }).catch((error) => setDownloadError((error as Error).message));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [download?.id, download?.status]);
  if (!models.length) return <p className="text-helper">Nenhum modelo público integrado é compatível com esta tarefa.</p>;
  const errors = model ? inputErrors(model.input_schema, config.parameters ?? {}) : [];
  return <div className="model-config-form">
    <label className="model-config-field">Modelo compatível com detecção
      <select className="input" disabled={busy} value={model?.id ?? ""} onChange={(e) => {
        const selected = models.find((entry) => entry.id === e.target.value);
        if (selected) useAutolabelingStore.getState().chooseModel(selected);
      }}>
        {!model && <option value="">Selecione um modelo</option>}
        {models.map((entry) => <option value={entry.id} key={entry.id}>{entry.name}</option>)}
      </select>
    </label>
    {model && <>
      <div className="model-catalog-card">
        <strong>{model.name}</strong><span className="text-helper">{model.description}</span>
        <span className={`badge ${model.availability === "configured" ? "badge-detection" : ""}`}>
          {model.provider_model ? (model.installed ? "Instalado · pronto para configurar" : "Disponível no catálogo Ollama")
            : model.availability === "configured" ? "Configurado · teste a inferência" : "Configuração necessária"}
        </span>
        {model.provider_model && <span className="text-helper">{model.provider_model} · {((model.download_size_bytes ?? 0) / 1_000_000_000).toFixed(1)} GB</span>}
        {model.provider_model && <a href={model.documentation_url} target="_blank" rel="noreferrer">Instalar o Ollama</a>}
        {model.reasons.map((reason) => <p key={reason} className="text-helper">{reason}</p>)}
        {model.provider_model && !model.installed && <button type="button" className="btn-secondary" disabled={busy || !model.provider_available || ["queued", "running"].includes(download?.status ?? "")}
          onClick={async () => {
            setDownloadError(null);
            try {
              const result = await api.post<NonNullable<typeof download>>(`/autolabeling/models/${encodeURIComponent(model.id)}/download`);
              setDownload(result);
              if (result.status === "succeeded") api.get<CatalogModel[]>("/autolabeling/models?task=detect_boxes").then((catalog) => useAutolabelingStore.setState({ catalog }));
            }
            catch (error) { setDownloadError((error as Error).message); }
          }}>{download?.status === "running" || download?.status === "queued" ? "Baixando…" : `Baixar ${model.provider_model}`}</button>}
        {download && <div role="status" className="text-helper">
          {download.progress}: {download.total > 0 ? `${(100 * download.completed / download.total).toFixed(0)}%` : "Preparando"}
          {download.total > 0 && <progress aria-label="Progresso do download" value={download.completed} max={download.total} style={{ width: "100%" }} />}
        </div>}
        {downloadError && <p role="alert" className="text-helper">{downloadError}</p>}
        {(model.requires_checkpoint || model.can_prepare) && <button type="button" className="btn-secondary" disabled={busy} onClick={() => setSetupOpen(true)}>Configurar modelo</button>}
      </div>
      <ModelConfigForm schema={model.input_schema} classes={classes} disabled={busy}
        value={{ ...schemaDefaults(model.input_schema), ...config.parameters }}
        onChange={(parameters) => setConfig((c) => ({ ...c, parameters }))} />
      {errors.length > 0 && <span className="text-helper">Selecione as classes e preencha os campos válidos para testar.</span>}
      <span className="text-helper">Serão geradas caixas para revisão. Máscaras não serão salvas como anotações de segmentação.</span>
      {setupOpen && <ModelSetupDialog model={model} onClose={() => setSetupOpen(false)} onSaved={(updated) => {
        useAutolabelingStore.setState((s) => ({ catalog: s.catalog.map((entry) => entry.id === updated.id ? updated : entry) }));
        setConfig((c) => (c.model_id ?? c.adapter) === updated.id ? { ...c, model_path: "" } : c);
      }} />}
    </>}
  </div>;
}
