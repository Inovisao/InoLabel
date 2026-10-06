import type { CocoLayout } from "../types";

const LAYOUTS: [CocoLayout, string, string][] = [
  ["roboflow", "Estilo Roboflow", "train/_annotations.coco.json com as imagens na mesma pasta."],
  ["images_dir", "Pasta images/", "_annotations.coco.json com as imagens em images/."],
];

interface Props {
  value: CocoLayout;
  onChange: (layout: CocoLayout) => void;
  disabled: boolean;
}

/** Onde ficam as imagens em relação ao _annotations.coco.json. */
export default function CocoLayoutSection({ value, onChange, disabled }: Props) {
  return (
    <div>
      <label className="text-label" style={{ display: "block", marginBottom: 6 }}>
        Organização do COCO
      </label>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {LAYOUTS.map(([id, label, desc]) => (
          <label key={id} style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer", fontSize: 13 }}>
            <input
              type="radio"
              name="coco-layout"
              checked={value === id}
              disabled={disabled}
              onChange={() => onChange(id)}
              style={{ accentColor: "var(--color-primary)", marginTop: 3 }}
            />
            <span>
              <strong>{label}</strong> <span style={{ color: "var(--color-muted)", fontSize: 12 }}>— {desc}</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
