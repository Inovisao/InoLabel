import { useState } from "react";
import { FolderOpen, CheckSquare, RotateCcw } from "lucide-react";
import type { ProjectEntry } from "../../shared/api/types";
import { PROJECT_MODE_LABELS } from "../../shared/modes";
import { formatDate, formatTime } from "./dates";

/** Linha da linha do tempo do Histórico. */
export default function TimelineRow({
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
            {PROJECT_MODE_LABELS[project.mode] ?? project.mode}
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
