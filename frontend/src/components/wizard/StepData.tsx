import { Folder, FileSearch } from "lucide-react";
import { api } from "../../api/client";
import type { WizardState } from "./Wizard";

interface Props {
  state: WizardState;
  onChange: (patch: Partial<WizardState>) => void;
}

export default function StepData({ state, onChange }: Props) {
  const browseFolder = async (field: "dataRoot" | "outputDir") => {
    try {
      const res = await api.get<{ path: string }>("/browse/folder");
      if (res.path) onChange({ [field]: res.path });
    } catch {
      /* usuário cancelou ou backend indisponível */
    }
  };

  const browseFile = async () => {
    try {
      const res = await api.get<{ path: string }>("/browse/file?ext=pt");
      if (res.path) onChange({ weightsPath: res.path });
    } catch {
      /* usuário cancelou ou backend indisponível */
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <PathField
        label="Pasta de dados"
        hint="Pasta com as imagens ou arquivo de vídeo a ser anotado."
        placeholder="/caminho/para/dados"
        value={state.dataRoot}
        onChange={(v) => onChange({ dataRoot: v })}
        onBrowse={() => browseFolder("dataRoot")}
        browseIcon="folder"
      />

      <PathField
        label="Pasta de saída"
        hint="Onde salvar os arquivos de anotação gerados."
        placeholder="output"
        value={state.outputDir}
        onChange={(v) => onChange({ outputDir: v })}
        onBrowse={() => browseFolder("outputDir")}
        browseIcon="folder"
      />

      <PathField
        label="Pesos do modelo (opcional)"
        hint="Arquivo .pt do YOLO para pré-anotar os frames automaticamente."
        placeholder="/caminho/para/model.pt"
        value={state.weightsPath}
        onChange={(v) => onChange({ weightsPath: v })}
        onBrowse={browseFile}
        browseIcon="file"
      />

      <label
        style={{ display: "flex", gap: 10, alignItems: "center", cursor: "pointer", userSelect: "none" }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: 4,
            border: `2px solid ${state.resumeExisting ? "var(--color-primary)" : "var(--color-border)"}`,
            background: state.resumeExisting ? "var(--color-primary)" : "var(--color-panel)",
            display: "flex",
            alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "background var(--motion-base), border-color var(--motion-base)",
              }}
          onClick={() => onChange({ resumeExisting: !state.resumeExisting })}
        >
          {state.resumeExisting && (
            <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
              <path d="M1 4l3 3 5-6" stroke="var(--color-text-inverse)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </div>
        <input
          type="checkbox"
          checked={state.resumeExisting}
          onChange={(e) => onChange({ resumeExisting: e.target.checked })}
          style={{ display: "none" }}
        />
        <span style={{ fontSize: 14, color: "var(--color-sidebar-text)" }}>
          Retomar anotações existentes nesta pasta
        </span>
      </label>
    </div>
  );
}

interface PathFieldProps {
  label: string;
  hint?: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
  onBrowse: () => void;
  browseIcon: "folder" | "file";
}

function PathField({ label, hint, placeholder, value, onChange, onBrowse, browseIcon }: PathFieldProps) {
  const Icon = browseIcon === "folder" ? Folder : FileSearch;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label className="text-label">{label}</label>
      {hint && <span className="text-helper">{hint}</span>}
      <div style={{ display: "flex", gap: 8, marginTop: hint ? 4 : 0 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          className="btn-icon"
          type="button"
          onClick={onBrowse}
          title="Explorar arquivos"
          style={{
            width: 40,
            height: 40,
            color: "var(--color-primary)",
          }}
        >
          <Icon size={18} strokeWidth={1.75} />
        </button>
      </div>
    </div>
  );
}
