import { Check } from "lucide-react";
/** Indicador das etapas do wizard (Modo → Dados → Configuração). */
export default function StepperBar({ current, labels }: { current: number; labels: string[] }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginTop: 24 }}>
      {labels.map((label, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            flex: i < labels.length - 1 ? 1 : undefined,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: i <= current ? "var(--color-primary)" : "var(--color-border)",
                color: i <= current ? "var(--color-text-inverse)" : "var(--color-placeholder)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                flexShrink: 0,
                transition: "background var(--motion-base)",
              }}
            >
              {i < current ? <Check size={14} strokeWidth={3} /> : i + 1}
            </div>
            <span
              style={{
                fontSize: 13,
                fontWeight: i === current ? 600 : 400,
                color: i <= current ? "var(--color-primary)" : "var(--color-placeholder)",
                transition: "color var(--motion-base)",
              }}
            >
              {label}
            </span>
          </div>
          {i < labels.length - 1 && <div className="stepper-connector" />}
        </div>
      ))}
    </div>
  );
}
