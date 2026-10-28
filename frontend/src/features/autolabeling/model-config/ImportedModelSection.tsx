import type { Dispatch, SetStateAction } from "react";
import type { ClassItem } from "../../../shared/api/types";
import type { ModelConfig } from "../types";
import RuntimeDiagnostics from "../RuntimeDiagnostics";

export default function ImportedModelSection({ config, setConfig, modelClasses, classes, busy, onBrowse, onInspect }: {
  config: ModelConfig; setConfig: Dispatch<SetStateAction<ModelConfig>>; modelClasses: string[];
  classes: ClassItem[]; busy: boolean; onBrowse: () => void; onInspect: () => void;
}) {
  return <div className="model-config-form">
    <strong>Checkpoint de detecção · YOLO</strong>
    <RuntimeDiagnostics />
    <label className="model-config-field">Checkpoint .pt
      <input className="input" value={config.model_path} disabled={busy} onChange={(e) => setConfig((c) => ({ ...c, model_path: e.target.value }))} />
    </label>
    <button type="button" className="btn-secondary" disabled={busy} onClick={onBrowse}>Selecionar arquivo</button>
    <span className="text-helper">Carregue apenas pesos de origem confiável.</span>
    <button type="button" className="btn-secondary" disabled={busy || !config.model_path} onClick={onInspect}>{busy ? "Aguarde…" : "Inspecionar modelo"}</button>
    {modelClasses.map((name) => <label key={name} className="model-config-field">{name} →
      <select className="input" disabled={busy} value={config.class_mapping[name] ?? ""}
        onChange={(e) => setConfig((c) => ({ ...c, class_mapping: { ...c.class_mapping, [name]: e.target.value || null } }))}>
        <option value="">Ignorar classe</option>
        {classes.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
      </select>
    </label>)}
    <label className="model-config-field">Confiança mínima
      <input className="input" type="number" min={0} max={1} step={0.05} disabled={busy} value={config.confidence}
        onChange={(e) => setConfig((c) => ({ ...c, confidence: Number(e.target.value) }))} />
    </label>
  </div>;
}
