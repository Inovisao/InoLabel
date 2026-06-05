import { useEffect, useState } from "react";
import { History, FolderOpen, CheckSquare, RotateCcw } from "lucide-react";
import PageShell from "../components/layout/PageShell";
import { api } from "../api/client";
import type { ProjectEntry } from "../api/types";

const MODE_LABELS: Record<string, string> = {
  detection: "Detecção",
  tracking: "Tracking",
  obb: "OBB",
  classification: "Classificação",
  unknown: "—",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function groupByPeriod(projects: ProjectEntry[]): { label: string; items: ProjectEntry[] }[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfWeek = new Date(startOfToday.getTime() - 6 * 24 * 60 * 60 * 1000);

  const toDate = (iso: string) => new Date(iso);

  const today = projects.filter((p) => toDate(p.last_modified) >= startOfToday);
  const thisWeek = projects.filter((p) => {
    const d = toDate(p.last_modified);
    return d >= startOfWeek && d < startOfToday;
  });
  const older = projects.filter((p) => toDate(p.last_modified) < startOfWeek);

  return [
    { label: "Hoje", items: today },
    { label: "Últimos 7 dias", items: thisWeek },
    { label: "Mais antigos", items: older },
  ].filter((g) => g.items.length > 0);
}

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
  onResume: (project: ProjectEntry) => void;
}

export default function HistoryPage({ activeNav, onNavigate, onResume }: Props) {
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const scanPath = localStorage.getItem("inolabel_output_root") || "output";

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.get<ProjectEntry[]>(
        `/session/projects?path=${encodeURIComponent(scanPath)}`
      );
      setProjects(data);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
            background: "var(--color-neutral, #F3F4F6)",
            padding: "1px 6px",
            borderRadius: 4,
            fontFamily: "var(--font-mono, monospace)",
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
        <EmptyState onNewProject={() => onNavigate("mode")} />
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

function TimelineRow({
  project,
  isLast,
  onResume,
}: {
  project: ProjectEntry;
  isLast: boolean;
  onResume: (p: ProjectEntry) => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "14px 20px",
        borderBottom: isLast ? "none" : "1px solid var(--color-border)",
        background: hovered ? "var(--color-hero-bg)" : "transparent",
        transition: "background 120ms",
      }}
    >
      {/* Icon */}
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 9,
          background: "var(--color-hero-bg)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <FolderOpen size={17} color="var(--color-primary)" strokeWidth={1.5} />
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 600,
            fontSize: 13,
            color: "var(--color-text)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {project.name}
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 3, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
            {MODE_LABELS[project.mode] ?? project.mode}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "var(--color-muted)" }}>
            <CheckSquare size={11} />
            {project.annotated_frames} frames
          </span>
          {project.classes.length > 0 && (
            <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
              {project.classes.slice(0, 3).join(", ")}
              {project.classes.length > 3 ? ` +${project.classes.length - 3}` : ""}
            </span>
          )}
        </div>
      </div>

      {/* Date */}
      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <div style={{ fontSize: 12, color: "var(--color-text)", fontWeight: 500 }}>
          {formatDate(project.last_modified)}
        </div>
        <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 2 }}>
          {formatTime(project.last_modified)}
        </div>
      </div>

      {/* Resume button — visible on hover */}
      <button
        className="btn-secondary"
        style={{
          flexShrink: 0,
          height: 32,
          fontSize: 12,
          display: "flex",
          alignItems: "center",
          gap: 5,
          opacity: hovered ? 1 : 0,
          transition: "opacity 120ms",
          pointerEvents: hovered ? "auto" : "none",
        }}
        onClick={() => onResume(project)}
        disabled={!project.data_path}
      >
        <RotateCcw size={12} />
        Retomar
      </button>
    </div>
  );
}

/* ── Empty state ─────────────────────────────────── */

function EmptyState({ onNewProject }: { onNewProject: () => void }) {
  return (
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
          Nenhuma sessão encontrada
        </div>
        <div style={{ fontSize: 14, color: "var(--color-muted)", lineHeight: 1.6, maxWidth: 400 }}>
          As sessões de anotação serão registradas aqui automaticamente após a
          primeira sessão concluída.
        </div>
      </div>
      <button className="btn-primary" style={{ marginTop: 8 }} onClick={onNewProject}>
        Iniciar primeira sessão →
      </button>
    </div>
  );
}
