import { Home, Sun, Moon, Bell } from "lucide-react";
import { useTheme } from "../../ui/ThemeContext";

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

        {/* Bell with badge */}
        <button
          className="btn-icon"
          title="Notificações"
          aria-label="Notificações"
          style={{ position: "relative" }}
        >
          <Bell size={16} />
          <span
            style={{
              position: "absolute",
              top: 6,
              right: 6,
              width: 8,
              height: 8,
              background: "var(--color-error-icon)",
              borderRadius: "50%",
              border: "2px solid var(--color-panel)",
            }}
          />
        </button>

        {/* Welcome pill */}
        <div
          style={{
            height: 36,
            padding: "0 14px",
            background: "var(--color-primary-light)",
            color: "var(--color-primary)",
            borderRadius: 999,
            display: "flex",
            alignItems: "center",
            fontSize: 13,
            fontWeight: 500,
            border: "1px solid color-mix(in srgb, var(--color-primary) 15%, transparent)",
            cursor: "default",
          }}
        >
          Bem-vindo(a)! 👋
        </div>
      </div>
    </header>
  );
}
