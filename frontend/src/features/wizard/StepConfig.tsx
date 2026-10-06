import { useState } from "react";
import { Plus, X } from "lucide-react";
import { DEFAULT_KEYPOINTS, parseKeypointNames, type WizardState } from "./wizardState";

interface Props {
  state: WizardState;
  onChange: (patch: Partial<WizardState>) => void;
}

export default function StepConfig({ state, onChange }: Props) {
  const [newClass, setNewClass] = useState("");

  const addClass = () => {
    const name = newClass.trim();
    if (!name || state.classes.includes(name)) return;
    // Projeto novo começa com o padrão da 1.0.0; ao retomar, vazio = pontos do projeto.
    const keypointNames =
      state.mode === "keypoint" && !state.outputDir && state.keypointNames[name] === undefined
        ? { ...state.keypointNames, [name]: DEFAULT_KEYPOINTS }
        : state.keypointNames;
    onChange({ classes: [...state.classes, name], keypointNames });
    setNewClass("");
  };

  const removeClass = (name: string) =>
    onChange({ classes: state.classes.filter((c) => c !== name) });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Classes */}
      <div>
        <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
          Classes de objetos
        </label>
        <span className="text-helper" style={{ display: "block", marginBottom: 10 }}>
          Defina as categorias para este projeto de anotação.
        </span>

        <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
          <input
            className="input"
            placeholder="Nome da classe (ex: pessoa)"
            value={newClass}
            onChange={(e) => setNewClass(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addClass()}
            style={{ flex: 1 }}
          />
          <button
            className="btn-primary"
            onClick={addClass}
            style={{ height: 40, padding: "0 14px", fontSize: 13 }}
            aria-label="Adicionar classe"
          >
            <Plus size={16} />
          </button>
        </div>

        {state.classes.length > 0 ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {state.classes.map((cls, i) => (
              <span
                key={cls}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "4px 10px 4px 8px",
                  background: "var(--color-primary-light)",
                  border: "1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)",
                  borderRadius: 999,
                  fontSize: 13,
                  color: "var(--color-primary)",
                  fontWeight: 500,
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: CLASS_PALETTE[i % CLASS_PALETTE.length],
                    flexShrink: 0,
                  }}
                />
                {cls}
                <button
                  onClick={() => removeClass(cls)}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    cursor: "pointer",
                    color: "var(--color-primary)",
                    display: "flex",
                    lineHeight: 1,
                    marginLeft: 2,
                    opacity: 0.65,
                  }}
                  aria-label={`Remover ${cls}`}
                >
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-helper" style={{ fontStyle: "italic" }}>
            Nenhuma classe adicionada ainda.
          </p>
        )}
      </div>

      {state.mode === "keypoint" && state.classes.length > 0 && (
        <div>
          <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
            Pontos de cada classe
          </label>
          <span className="text-helper" style={{ display: "block", marginBottom: 10 }}>
            Nomes separados por vírgula, na ordem em que serão clicados.
            {state.outputDir && " Deixe vazio para manter os pontos já salvos no projeto."}
          </span>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {state.classes.map((cls) => {
              const count = parseKeypointNames(state.keypointNames[cls]).length;
              return (
                <div key={cls} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 120, fontSize: 13, fontWeight: 600, flexShrink: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
                    {cls}
                  </span>
                  <input
                    className="input"
                    aria-label={`Pontos da classe ${cls}`}
                    placeholder={state.outputDir ? "pontos do projeto" : DEFAULT_KEYPOINTS}
                    value={state.keypointNames[cls] ?? ""}
                    onChange={(e) =>
                      onChange({ keypointNames: { ...state.keypointNames, [cls]: e.target.value } })
                    }
                    style={{ flex: 1, fontSize: 13 }}
                  />
                  <span className="text-mono" style={{ width: 64, fontSize: 12, color: "var(--color-muted)", flexShrink: 0 }}>
                    {count ? `${count} pt${count > 1 ? "s" : ""}` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Confidence threshold */}
      <div>
        <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
          Confiança mínima do modelo:{" "}
          <span
            style={{
              color: "var(--color-primary)",
              fontFamily: "var(--font-mono)",
              fontSize: 14,
            }}
          >
            {state.confidence.toFixed(2)}
          </span>
        </label>
        <span className="text-helper" style={{ display: "block", marginBottom: 10 }}>
          Detecções abaixo desse limite serão descartadas automaticamente.
        </span>
        <input
          type="range"
          min={0.05}
          max={0.95}
          step={0.05}
          value={state.confidence}
          onChange={(e) => onChange({ confidence: parseFloat(e.target.value) })}
          style={{
            width: "100%",
            accentColor: "var(--color-primary)",
            height: 4,
            cursor: "pointer",
          }}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 4,
          }}
        >
          <span className="text-mono">0.05</span>
          <span className="text-mono">0.95</span>
        </div>
      </div>
    </div>
  );
}

const CLASS_PALETTE = [
  "#2563EB", "#16A34A", "#EA580C", "#DC2626",
  "#9333EA", "#0D9488", "#CA8A04", "#DB2777",
];
