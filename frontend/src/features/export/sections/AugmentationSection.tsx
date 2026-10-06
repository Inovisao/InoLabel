import type { AugmentationOption } from "../../../shared/api/types";
import CheckboxRow, { subPanel } from "./CheckboxRow";

interface Props {
  enabled: boolean;
  onEnabled: (enabled: boolean) => void;
  catalog: AugmentationOption[];
  selected: string[];
  onToggle: (key: string) => void;
  copies: number;
  onCopies: (copies: number) => void;
  isKeypoint: boolean;
  disabled: boolean;
}

/** Augmentation: quais transformações e quantas cópias por imagem de treino. */
export default function AugmentationSection(p: Props) {
  return (
    <div>
      <CheckboxRow
        label="Gerar imagens aumentadas (augmentation)"
        checked={p.enabled}
        disabled={p.disabled}
        onChange={p.onEnabled}
      />
      {p.enabled && (
        <div style={{ ...subPanel, marginTop: 10, gap: 8 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {p.catalog.map((a) => {
              const on = p.selected.includes(a.key);
              return (
                <button
                  key={a.key}
                  type="button"
                  title={a.description}
                  aria-pressed={on}
                  disabled={p.disabled}
                  onClick={() => p.onToggle(a.key)}
                  style={{
                    fontSize: 12,
                    padding: "4px 10px",
                    borderRadius: 999,
                    border: `1px solid ${on ? "var(--color-primary)" : "var(--color-border)"}`,
                    background: on ? "var(--color-primary-light)" : "var(--color-panel)",
                    color: on ? "var(--color-primary)" : "var(--color-text)",
                    cursor: "pointer",
                    fontFamily: "var(--font-sans)",
                  }}
                >
                  {a.label}
                </button>
              );
            })}
            {p.catalog.length === 0 && <span className="text-helper">Catálogo de augmentation indisponível.</span>}
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
            Cópias por imagem
            <select
              className="input"
              value={p.copies}
              disabled={p.disabled}
              onChange={(e) => p.onCopies(Number(e.target.value))}
              style={{ width: 70, height: 30, fontSize: 12 }}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
          {p.isKeypoint && p.selected.some((k) => k.startsWith("flip")) && (
            <span className="text-helper" style={{ color: "var(--color-warning)" }}>
              Espelhar não troca os nomes dos pontos: um ponto "esquerdo" passa a ficar à direita.
            </span>
          )}
          <span className="text-helper">
            Só nas imagens de treino do YOLO (val/test e COCO ficam sem cópias, para não vazar dados na validação).
          </span>
        </div>
      )}
    </div>
  );
}
