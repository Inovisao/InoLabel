import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { api } from "../../../shared/api/client";
import type { CatalogModel } from "../types";

export default function ModelSetupDialog({ model, onClose, onSaved }: {
  model: CatalogModel; onClose: () => void; onSaved: (model: CatalogModel) => void;
}) {
  const [path, setPath] = useState(model.setup.model_path);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return <Dialog.Root open onOpenChange={(open) => { if (!open && !busy) onClose(); }}>
    <Dialog.Portal><Dialog.Overlay className="modal-overlay" />
      <Dialog.Content className="modal-content" style={{ width: 500, padding: 24, display: "grid", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Dialog.Title>Configurar {model.name}</Dialog.Title>
          <button type="button" className="btn-icon" aria-label="Fechar configuração" disabled={busy} onClick={onClose}><X size={16} /></button>
        </div>
        <Dialog.Description className="text-helper">{model.can_prepare
          ? "Prepare o runtime local conforme as instruções. A preparação pode baixar os pesos e levar vários minutos."
          : "Registre os pesos locais para este modelo. A configuração fica nesta instalação; os prompts pertencem a cada projeto."}</Dialog.Description>
        <a href={model.documentation_url} target="_blank" rel="noreferrer">Instruções oficiais e acesso aos pesos</a>
        {model.setup_instructions && <p className="text-helper">{model.setup_instructions}</p>}
        {model.requires_checkpoint && <><label className="model-config-field">Checkpoint oficial .pt
          <input className="input" value={path} disabled={busy} onChange={(e) => setPath(e.target.value)} />
        </label>
        <button type="button" className="btn-secondary" disabled={busy} onClick={async () => {
          setError(null);
          try { const result = await api.get<{ path: string }>("/browse/file"); if (result.path) setPath(result.path); }
          catch (e) { setError((e as Error).message); }
        }}>Selecionar arquivo</button></>}
        {model.reasons.map((reason) => <p key={reason} className="text-helper">{reason}</p>)}
        <span className="text-helper">{model.can_prepare
          ? "Configure as variáveis do servidor antes de iniciar o aplicativo. A chave fica no backend. Preparar modelo autoriza o download e cache dos pesos; a inferência será local. Acesso à rede pode ser necessário para autenticação."
          : "Use apenas pesos obtidos de uma origem confiável."}</span>
        {error && <div role="alert" className="alert alert-error">{error}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" className="btn-secondary" disabled={busy} onClick={onClose}>Cancelar</button>
          <button type="button" className="btn-primary" disabled={busy || (!model.can_prepare && !path.trim())} onClick={async () => {
            setBusy(true); setError(null);
            try {
              const base = `/autolabeling/models/${encodeURIComponent(model.id)}`;
              const updated = model.can_prepare ? await api.post<CatalogModel>(`${base}/prepare`)
                : await api.put<CatalogModel>(`${base}/setup`, { model_path: path });
              onSaved(updated); onClose();
            } catch (e) { setError((e as Error).message); }
            finally { setBusy(false); }
          }}>{busy ? (model.can_prepare ? "Preparando modelo…" : "Salvando…") : (model.can_prepare ? "Preparar modelo" : "Salvar configuração")}</button>
        </div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
