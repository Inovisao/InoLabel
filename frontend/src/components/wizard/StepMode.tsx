import { ScanLine, BoxSelect, Diamond, Grid2X2 } from "lucide-react";
import type { TaskMode } from "../../api/types";

interface ModeOption {
  id: TaskMode;
  label: string;
  description: string;
  icon: React.ElementType;
  iconBg: string;
  iconColor: string;
}

const MODES: ModeOption[] = [
  {
    id: "tracking",
    label: "Rastreamento",
    description: "Mantém identidade de objetos entre frames usando BYTETracker.",
    icon: ScanLine,
    iconBg: "#DBEAFE",
    iconColor: "#3B82F6",
  },
  {
    id: "detection",
    label: "Detecção padrão",
    description: "Bounding boxes independentes por frame, sem track_id.",
    icon: BoxSelect,
    iconBg: "#DBEAFE",
    iconColor: "#3B82F6",
  },
  {
    id: "obb",
    label: "Detecção orientada (OBB)",
    description: "Caixas rotacionadas com ângulo, exportáveis em formato YOLO OBB.",
    icon: Diamond,
    iconBg: "#DCFCE7",
    iconColor: "#22C55E",
  },
  {
    id: "classification",
    label: "Classificação",
    description: "Organiza imagens em subpastas por classe com um keypress.",
    icon: Grid2X2,
    iconBg: "#FEF3C7",
    iconColor: "#F59E0B",
  },
];

interface Props {
  value: TaskMode;
  onChange: (m: TaskMode) => void;
}

export default function StepMode({ value, onChange }: Props) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
      }}
    >
      {MODES.map((mode) => {
        const selected = value === mode.id;
        const Icon = mode.icon;
        return (
          <button
            key={mode.id}
            onClick={() => onChange(mode.id)}
            style={{
              display: "flex",
              flexDirection: "row",
              alignItems: "flex-start",
              gap: 14,
              padding: 20,
              background: selected ? "var(--color-primary-light)" : "var(--color-panel)",
              border: `1px solid ${selected ? "var(--color-primary)" : "var(--color-border)"}`,
              borderRadius: "var(--radius-lg)",
              cursor: "pointer",
              textAlign: "left",
              position: "relative",
              transition: "background 150ms, border-color 150ms",
              width: "100%",
            }}
            onMouseEnter={(e) => {
              if (!selected) {
                (e.currentTarget as HTMLButtonElement).style.background = "#FAFAFA";
              }
            }}
            onMouseLeave={(e) => {
              if (!selected) {
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-panel)";
              }
            }}
          >
            {/* Radio indicator */}
            <div
              style={{
                position: "absolute",
                top: 14,
                right: 14,
                width: 20,
                height: 20,
                borderRadius: "50%",
                border: `2px solid ${selected ? "var(--color-primary)" : "#D1D5DB"}`,
                background: selected ? "var(--color-primary)" : "transparent",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "border-color 150ms, background 150ms",
              }}
            >
              {selected && (
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "#fff",
                  }}
                />
              )}
            </div>

            {/* Icon box */}
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 10,
                background: mode.iconBg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon size={24} color={mode.iconColor} strokeWidth={1.75} />
            </div>

            {/* Text */}
            <div style={{ flex: 1, minWidth: 0, paddingRight: 20 }}>
              <div
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: selected ? "var(--color-primary)" : "var(--color-text)",
                  marginBottom: 4,
                  lineHeight: 1.3,
                  transition: "color 150ms",
                }}
              >
                {mode.label}
              </div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 400,
                  color: "var(--color-muted)",
                  lineHeight: 1.45,
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {mode.description}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
