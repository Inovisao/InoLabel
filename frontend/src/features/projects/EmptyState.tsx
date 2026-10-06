import type { ReactNode } from "react";

interface Props {
  icon: ReactNode;
  title: string;
  text: string;
  textMaxWidth: number;
  actionLabel: string;
  onAction: () => void;
}

/** Página sem itens: ícone, explicação e o botão para começar. */
export default function EmptyState({ icon, title, text, textMaxWidth, actionLabel, onAction }: Props) {
  return (
    <div
      className="surface-card"
      style={{
        padding: "60px 32px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        gap: 16,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 16,
          background: "var(--color-hero-bg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 8 }}>{title}</div>
        <div style={{ fontSize: 14, color: "var(--color-muted)", lineHeight: 1.6, maxWidth: textMaxWidth }}>{text}</div>
      </div>
      <button className="btn-primary" style={{ marginTop: 8 }} onClick={onAction}>
        {actionLabel}
      </button>
    </div>
  );
}
