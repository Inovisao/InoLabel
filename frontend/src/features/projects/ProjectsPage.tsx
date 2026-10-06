import { FolderOpen, RefreshCw } from "lucide-react";
import PageShell from "../../shared/layout/PageShell";
import { useWorkspaceStore } from "../workspace/store";
import type { ProjectEntry } from "../../shared/api/types";
import EmptyState from "./EmptyState";
import ProjectCard from "./ProjectCard";
import { useWorkspaceProjects } from "./useWorkspaceProjects";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
  onResume: (project: ProjectEntry) => void;
}

export default function ProjectsPage({ activeNav, onNavigate, onResume }: Props) {
  const chooseAnother = useWorkspaceStore((s) => s.chooseAnother);
  const { workspace, path: scanPath, projects, loading, reload } = useWorkspaceProjects();

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

      {/* Workspace atual */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, alignItems: "center" }}>
        <FolderOpen size={16} style={{ color: "var(--color-muted)", flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{workspace?.name}</div>
          <div className="text-mono" style={{ fontSize: 12, color: "var(--color-muted)", wordBreak: "break-all" }}>
            {scanPath}
          </div>
        </div>
        <button className="btn-secondary" onClick={chooseAnother} style={{ height: 38, whiteSpace: "nowrap" }}>
          Trocar workspace
        </button>
        <button className="btn-secondary" onClick={() => reload()} style={{ height: 38, display: "flex", alignItems: "center", gap: 6 }}>
          <RefreshCw size={14} />
          Atualizar
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "var(--color-muted)", fontSize: 14 }}>
          Carregando projetos…
        </div>
      ) : projects.length === 0 ? (
        <EmptyState
          icon={<FolderOpen size={32} color="var(--color-primary)" strokeWidth={1.5} />}
          title="Nenhum projeto encontrado"
          text="Os projetos salvos aparecerão aqui. Confirme se a pasta de saída indicada acima está correta, ou inicie uma nova sessão de anotação."
          textMaxWidth={380}
          actionLabel="Novo projeto →"
          onAction={() => onNavigate("mode")}
        />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 16,
          }}
        >
          {projects.map((p) => (
            <ProjectCard key={p.path} project={p} onResume={onResume} />
          ))}
        </div>
      )}
    </PageShell>
  );
}

/* ── Project card ────────────────────────────────── */
