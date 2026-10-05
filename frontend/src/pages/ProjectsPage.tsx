import { useEffect, useState } from "react";
import { FolderOpen, RefreshCw, Search, Tag, CheckSquare, Clock } from "lucide-react";
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

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return "agora mesmo";
  if (mins < 60) return `há ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `há ${hrs}h`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "ontem";
  if (days < 30) return `há ${days} dias`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
  onResume: (project: ProjectEntry) => void;
}

export default function ProjectsPage({ activeNav, onNavigate, onResume }: Props) {
  const [projects, setProjects] = useState<ProjectEntry[]>([]);
  const [scanPath, setScanPath] = useState<string>(
    () => localStorage.getItem("inolabel_output_root") || "output"
  );
  const [inputPath, setInputPath] = useState(scanPath);
  const [loading, setLoading] = useState(false);

  const load = async (path: string) => {
    setLoading(true);
    try {
      const data = await api.get<ProjectEntry[]>(`/session/projects?path=${encodeURIComponent(path)}`);
      setProjects(data);
    } catch {
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(scanPath);
  }, [scanPath]);

  const handleSearch = () => {
    const p = inputPath.trim() || "output";
    localStorage.setItem("inolabel_output_root", p);
    setScanPath(p);
  };

  const handleBrowse = async () => {
    try {
      const res = await api.get<{ path: string }>("/browse/folder");
      if (res.path) {
        setInputPath(res.path);
        localStorage.setItem("inolabel_output_root", res.path);
        setScanPath(res.path);
      }
    } catch {
      // browse not available (e.g. headless env)
    }
  };

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

      {/* Search bar */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 24,
          alignItems: "center",
        }}
      >
        <div style={{ position: "relative", flex: 1 }}>
          <Search
            size={15}
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--color-muted)",
            }}
          />
          <input
            className="input"
            value={inputPath}
            onChange={(e) => setInputPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Pasta de saída (ex: output)"
            style={{
              paddingLeft: 36,
              paddingRight: 12,
              height: 38,
              fontSize: 13,
            }}
          />
        </div>
        <button className="btn-secondary" onClick={handleBrowse} style={{ height: 38, whiteSpace: "nowrap" }}>
          Procurar pasta
        </button>
        <button className="btn-secondary" onClick={handleSearch} style={{ height: 38, display: "flex", alignItems: "center", gap: 6 }}>
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
        <EmptyState onNewProject={() => onNavigate("mode")} />
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

function ProjectCard({ project, onResume }: { project: ProjectEntry; onResume: (p: ProjectEntry) => void }) {
  return (
    <div
      className="surface-card surface-card-interactive"
      style={{
        padding: "20px 20px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: "var(--color-hero-bg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <FolderOpen size={20} color="var(--color-primary)" strokeWidth={1.5} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 14,
              color: "var(--color-text)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={project.name}
          >
            {project.name}
          </div>
          <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
            {MODE_LABELS[project.mode] ?? project.mode}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 16 }}>
        <Stat icon={<CheckSquare size={13} />} label={`${project.annotated_frames} frames anotados`} />
        <Stat icon={<Clock size={13} />} label={formatRelative(project.last_modified)} />
      </div>

      {/* Classes */}
      {project.classes.length > 0 && (
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
          <Tag size={11} color="var(--color-muted)" style={{ flexShrink: 0 }} />
          {project.classes.slice(0, 5).map((cls) => (
            <span
              key={cls}
              style={{
                fontSize: 11,
                padding: "2px 8px",
                background: "var(--color-hero-bg)",
                color: "var(--color-primary)",
                borderRadius: 999,
                fontWeight: 500,
              }}
            >
              {cls}
            </span>
          ))}
          {project.classes.length > 5 && (
            <span style={{ fontSize: 11, color: "var(--color-muted)" }}>
              +{project.classes.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Action */}
      <button
        className="btn-primary"
        style={{ width: "100%", marginTop: 4 }}
        onClick={() => onResume(project)}
        disabled={!project.data_path}
        title={!project.data_path ? "Pasta de imagens não localizada (projeto antigo)" : undefined}
      >
        Continuar →
      </button>
      {!project.data_path && (
        <div style={{ fontSize: 11, color: "var(--color-muted)", textAlign: "center", marginTop: -8 }}>
          Pasta de imagens não salva — configure manualmente
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "var(--color-muted)" }}>
      {icon}
      <span>{label}</span>
    </div>
  );
}

/* ── Empty state ─────────────────────────────────── */

function EmptyState({ onNewProject }: { onNewProject: () => void }) {
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
        <FolderOpen size={32} color="var(--color-primary)" strokeWidth={1.5} />
      </div>
      <div>
        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 8 }}>
          Nenhum projeto encontrado
        </div>
        <div style={{ fontSize: 14, color: "var(--color-muted)", lineHeight: 1.6, maxWidth: 380 }}>
          Os projetos salvos aparecerão aqui. Confirme se a pasta de saída
          indicada acima está correta, ou inicie uma nova sessão de anotação.
        </div>
      </div>
      <button className="btn-primary" style={{ marginTop: 8 }} onClick={onNewProject}>
        Novo projeto →
      </button>
    </div>
  );
}
