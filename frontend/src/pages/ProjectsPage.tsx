import { FolderOpen } from "lucide-react";
import PageShell from "../components/layout/PageShell";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
}

export default function ProjectsPage({ activeNav, onNavigate }: Props) {
  return (
    <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Projetos">
      {/* Hero */}
      <div
        style={{
          background: "var(--color-hero-bg)",
          borderRadius: "var(--radius-xl)",
          padding: "28px 32px",
          marginBottom: 24,
        }}
      >
        <h1 className="text-display" style={{ marginBottom: 8 }}>Projetos</h1>
        <p className="text-page-subtitle">Gerencie e retome seus projetos de anotação.</p>
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
          <FolderOpen size={32} color="var(--color-primary)" strokeWidth={1.5} />
        </div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 8 }}>
            Nenhum projeto encontrado
          </div>
          <div
            style={{
              fontSize: 14,
              color: "var(--color-muted)",
              lineHeight: 1.6,
              maxWidth: 380,
            }}
          >
            Os projetos salvos aparecerão aqui. Inicie uma nova sessão de anotação
            para criar seu primeiro projeto.
          </div>
        </div>
        <button
          className="btn-primary"
          style={{ marginTop: 8 }}
          onClick={() => onNavigate("mode")}
        >
          Novo projeto →
        </button>
      </div>
    </PageShell>
  );
}
