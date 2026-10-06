import { FolderOpen, Tag, CheckSquare, Clock } from "lucide-react";
import type { ProjectEntry } from "../../shared/api/types";
import { PROJECT_MODE_LABELS } from "../../shared/modes";
import { formatRelative } from "./dates";

/** Cartão de um projeto do workspace, com o botão de continuar. */
export default function ProjectCard({ project, onResume }: { project: ProjectEntry; onResume: (p: ProjectEntry) => void }) {
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
            {PROJECT_MODE_LABELS[project.mode] ?? project.mode}
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
