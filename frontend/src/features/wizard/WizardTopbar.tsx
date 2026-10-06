import { Home, Sun, Moon } from "lucide-react";
import { useTheme } from "../../shared/ui/ThemeContext";

interface Props {
  breadcrumb?: string;
}

export default function WizardTopbar({ breadcrumb = "Início" }: Props) {
  const { isDark, toggleTheme } = useTheme();
  const ThemeIcon = isDark ? Sun : Moon;
  const themeLabel = isDark ? "Ativar tema claro" : "Ativar tema escuro";

  return (
    <header
      style={{
        height: 56,
        background: "var(--color-panel)",
        borderBottom: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
        flexShrink: 0,
        userSelect: "none",
        gap: 8,
      }}
    >
      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <Home size={16} color="var(--color-muted)" />
        <span
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: "var(--color-sidebar-text)",
          }}
        >
          {breadcrumb}
        </span>
      </div>

      {/* Right actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginLeft: "auto",
        }}
      >
        <button
          className="btn-icon"
          title={themeLabel}
          aria-label={themeLabel}
          onClick={toggleTheme}
        >
          <ThemeIcon size={16} />
        </button>
      </div>
    </header>
  );
}
