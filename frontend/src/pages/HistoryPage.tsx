import { History } from "lucide-react";
import PageShell from "../components/layout/PageShell";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
}

export default function HistoryPage({ activeNav, onNavigate }: Props) {
  return (
    <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Histórico">
      {/* Hero */}
      <div
        style={{
          background: "var(--color-hero-bg)",
          borderRadius: "var(--radius-xl)",
          padding: "28px 32px",
          marginBottom: 24,
        }}
      >
        <h1 className="text-display" style={{ marginBottom: 8 }}>Histórico</h1>
        <p className="text-page-subtitle">Acompanhe as alterações feitas nas suas sessões de anotação.</p>
      </div>

      {/* Empty state */}
      <div
        style={{
          background: "var(--color-panel)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-xl)",
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
          <History size={32} color="var(--color-primary)" strokeWidth={1.5} />
        </div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 8 }}>
            Histórico indisponível
          </div>
          <div
            style={{
              fontSize: 14,
              color: "var(--color-muted)",
              lineHeight: 1.6,
              maxWidth: 400,
            }}
          >
            O rastreamento de histórico de edições será implementado em uma próxima
            versão do InoLabel. Por enquanto, as anotações são salvas automaticamente
            a cada operação.
          </div>
        </div>
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "6px 14px",
            background: "#FEF3C7",
            border: "1px solid #FDE68A",
            borderRadius: 999,
            fontSize: 12,
            color: "#92400E",
            fontWeight: 500,
          }}
        >
          Em desenvolvimento
        </div>
      </div>
    </PageShell>
  );
}
