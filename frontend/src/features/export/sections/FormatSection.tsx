import { CheckCircle } from "lucide-react";
import type { ExportFormat } from "../types";

const FORMATS: { id: ExportFormat; label: string; keypointLabel: string; desc: string }[] = [
  {
    id: "yolo",
    label: "YOLO TXT",
    keypointLabel: "YOLO Pose",
    desc: "Um arquivo .txt por imagem com bboxes normalizadas. Compatível com Ultralytics.",
  },
  {
    id: "coco",
    label: "COCO JSON",
    keypointLabel: "COCO Keypoints",
    desc: "Arquivo _annotations.coco.json no formato MS COCO. Compatível com torchvision.",
  },
];

interface Props {
  selected: ExportFormat[];
  onToggle: (format: ExportFormat) => void;
  isKeypoint: boolean;
  disabled: boolean;
}

/** Formatos a gerar (um ou os dois). */
export default function FormatSection({ selected, onToggle, isKeypoint, disabled }: Props) {
  return (
    <div>
      <label className="text-label" style={{ display: "block", marginBottom: 10 }}>
        Formatos de saída
      </label>
      <div style={{ display: "flex", gap: 10 }}>
        {FORMATS.map((f) => {
          const sel = selected.includes(f.id);
          return (
            <button
              key={f.id}
              onClick={() => onToggle(f.id)}
              disabled={disabled}
              aria-pressed={sel}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: 4,
                padding: "12px 14px",
                background: sel ? "var(--color-primary-light)" : "var(--color-bg)",
                border: `1px solid ${sel ? "var(--color-primary)" : "var(--color-border)"}`,
                borderRadius: "var(--radius-md)",
                cursor: disabled ? "not-allowed" : "pointer",
                textAlign: "left",
                fontFamily: "var(--font-sans)",
                transition: "background var(--motion-base), border-color var(--motion-base)",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: sel ? "var(--color-primary)" : "var(--color-text)" }}>
                  {isKeypoint ? f.keypointLabel : f.label}
                </span>
                {sel && <CheckCircle size={13} color="var(--color-primary)" />}
              </span>
              <span style={{ fontSize: 11, color: "var(--color-muted)", lineHeight: 1.4 }}>{f.desc}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
