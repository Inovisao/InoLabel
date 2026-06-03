import type { WizardState } from "./Wizard";

interface Props {
  state: WizardState;
  onChange: (patch: Partial<WizardState>) => void;
}

export default function StepData({ state, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Field
        label="Pasta de dados"
        hint="Caminho para a pasta com as imagens ou o arquivo de vídeo."
        placeholder="/caminho/para/dados"
        value={state.dataRoot}
        onChange={(v) => onChange({ dataRoot: v })}
      />

      <Field
        label="Pasta de saída"
        hint="Onde salvar os arquivos de anotação."
        placeholder="output"
        value={state.outputDir}
        onChange={(v) => onChange({ outputDir: v })}
      />

      <Field
        label="Pesos do modelo (opcional)"
        hint="Arquivo .pt do YOLO para pré-anotar os frames automaticamente."
        placeholder="/caminho/para/model.pt"
        value={state.weightsPath}
        onChange={(v) => onChange({ weightsPath: v })}
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
            transition: "background 150ms, border-color 150ms",
          }}
          onClick={() => onChange({ resumeExisting: !state.resumeExisting })}
        >
          {state.resumeExisting && (
            <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
              <path d="M1 4l3 3 5-6" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
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

function Field({
  label,
  hint,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  placeholder?: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label className="text-label">{label}</label>
      {hint && <span className="text-helper">{hint}</span>}
      <input
        className="input"
        style={{ marginTop: hint ? 4 : 0 }}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
