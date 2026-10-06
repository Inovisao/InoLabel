import { History } from "lucide-react";
import PageShell from "../../shared/layout/PageShell";
import type { ProjectEntry } from "../../shared/api/types";
import { groupByPeriod } from "./dates";
import EmptyState from "./EmptyState";
import TimelineRow from "./TimelineRow";
import { useWorkspaceProjects } from "./useWorkspaceProjects";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
  onResume: (project: ProjectEntry) => void;
}

export default function HistoryPage({ activeNav, onNavigate, onResume }: Props) {
  const { path: scanPath, projects, loading, reload } = useWorkspaceProjects();

  const groups = groupByPeriod(projects);

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
        <p className="text-page-subtitle">
          Acompanhe as sessões de anotação ordenadas por atividade recente.
        </p>
      </div>

      {/* Hint about scan path */}
      <div style={{ fontSize: 12, color: "var(--color-muted)", marginBottom: 16 }}>
        Exibindo sessões de{" "}
        <code
          style={{
            background: "var(--color-neutral-active)",
            padding: "1px 6px",
            borderRadius: 4,
            fontFamily: "var(--font-mono)",
          }}
        >
          {scanPath}
        </code>
        {" — "}
        <button
          style={{
            border: "none",
            background: "none",
            color: "var(--color-primary)",
            cursor: "pointer",
            fontSize: 12,
            padding: 0,
            fontWeight: 500,
          }}
          onClick={() => onNavigate("projects")}
        >
          alterar em Projetos
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--color-muted)", fontSize: 14 }}>
          Carregando histórico…
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={<History size={32} color="var(--color-primary)" strokeWidth={1.5} />}
          title="Nenhuma sessão encontrada"
          text="As sessões de anotação serão registradas aqui automaticamente após a primeira sessão concluída."
          textMaxWidth={400}
          actionLabel="Iniciar primeira sessão →"
          onAction={() => onNavigate("mode")}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
          {groups.map((group) => (
            <section key={group.label}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--color-muted)",
                  marginBottom: 12,
                  paddingLeft: 2,
                }}
              >
                {group.label}
              </div>
              <div
                style={{
                  background: "var(--color-panel)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-xl)",
                  overflow: "hidden",
                }}
              >
                {group.items.map((project, idx) => (
                  <TimelineRow
                    key={project.path}
                    project={project}
                    isLast={idx === group.items.length - 1}
                    onResume={onResume}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </PageShell>
  );
}

/* ── Timeline row ────────────────────────────────── */
