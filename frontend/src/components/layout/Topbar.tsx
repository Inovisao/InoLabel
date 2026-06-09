import { ChevronLeft, ChevronRight, Save, Download, Settings, LogOut, Sun, Moon } from "lucide-react";
import { useSessionStore } from "../../stores/session";
import { useAnnotationStore } from "../../stores/annotation";
import { useToast } from "../../ui/ToastContext";
import { useTheme } from "../../ui/ThemeContext";

const MODE_LABELS: Record<string, string> = {
  tracking: "Rastreamento",
  detection: "Detecção",
  obb: "OBB",
  classification: "Classificação",
};

interface Props {
  onExport: () => void;
  onSettings: () => void;
  onStop?: () => void;
}

export default function Topbar({ onExport, onSettings, onStop }: Props) {
  const mode = useSessionStore((s) => s.mode);
  const { frame, loading, prevFrame, nextFrame } = useAnnotationStore();
  const { toast } = useToast();
  const { isDark, toggleTheme } = useTheme();
  const ThemeIcon = isDark ? Sun : Moon;
  const themeLabel = isDark ? "Ativar tema claro" : "Ativar tema escuro";

  const handleSave = () => {
    toast("Anotações salvas automaticamente a cada operação.", "success");
  };

  return (
    <header
      style={{
        height: 56,
        background: "var(--color-panel)",
        borderBottom: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: 8,
        flexShrink: 0,
        userSelect: "none",
      }}
    >
      {/* Stop session */}
      {onStop && (
        <>
          <button
            className="btn-icon"
            onClick={onStop}
            title="Encerrar sessão"
            aria-label="Encerrar sessão"
            style={{ color: "var(--color-muted)" }}
          >
            <LogOut size={15} />
          </button>
          <div style={{ width: 1, height: 24, background: "var(--color-border)", margin: "0 4px" }} />
        </>
      )}

      {/* Mode badge */}
      {mode && (
        <span className={`badge badge-${mode}`}>
          {MODE_LABELS[mode] ?? mode}
        </span>
      )}

      {/* Filename */}
      {frame?.filename && (
        <span
          style={{
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            color: "var(--color-muted)",
            maxWidth: 240,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {frame.filename}
        </span>
      )}

      {/* Frame navigation */}
      <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: "auto" }}>
        <button
          className="btn-icon"
          onClick={prevFrame}
          disabled={loading || !frame || frame.index === 0}
          title="Frame anterior (A / ←)"
          aria-label="Frame anterior"
        >
          <ChevronLeft size={16} />
        </button>

        {frame ? (
          <span
            style={{
              minWidth: 72,
              textAlign: "center",
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {frame.index + 1} / {frame.total}
          </span>
        ) : (
          <span style={{ minWidth: 72, textAlign: "center", fontSize: 12, color: "var(--color-muted)" }}>
            — / —
          </span>
        )}

        <button
          className="btn-icon"
          onClick={nextFrame}
          disabled={loading || !frame || frame.index >= (frame.total ?? 1) - 1}
          title="Próximo frame (D / →)"
          aria-label="Próximo frame"
        >
          <ChevronRight size={16} />
        </button>
      </div>

      <div style={{ width: 1, height: 24, background: "var(--color-border)", margin: "0 4px" }} />

      <div style={{ display: "flex", gap: 4 }}>
        <button
          className="btn-icon"
          title={themeLabel}
          aria-label={themeLabel}
          onClick={toggleTheme}
        >
          <ThemeIcon size={15} />
        </button>
        <button
          className="btn-icon"
          title="Salvar (Ctrl+S)"
          aria-label="Salvar"
          onClick={handleSave}
        >
          <Save size={15} />
        </button>
        <button
          className="btn-icon"
          title="Exportar dataset (Ctrl+E)"
          aria-label="Exportar dataset"
          onClick={onExport}
        >
          <Download size={15} />
        </button>
        <button
          className="btn-icon"
          title="Configurações (Ctrl+,)"
          aria-label="Configurações"
          onClick={onSettings}
        >
          <Settings size={15} />
        </button>
      </div>
    </header>
  );
}
