import {
  LayoutGrid, Database, Settings, Folder,
  History, HelpCircle, Keyboard,
} from "lucide-react";
import { useTheme } from "../../ui/ThemeContext";

interface NavItem {
  id: string;
  icon: React.ElementType;
  label: string;
}

const NAV_GROUPS: NavItem[][] = [
  [
    { id: "mode",   icon: LayoutGrid, label: "Modo" },
    { id: "data",   icon: Database,   label: "Dados" },
    { id: "config", icon: Settings,   label: "Configuração" },
  ],
  [
    { id: "projects", icon: Folder,  label: "Projetos" },
    { id: "history",  icon: History, label: "Histórico" },
  ],
  [
    { id: "help",      icon: HelpCircle, label: "Ajuda" },
    { id: "shortcuts", icon: Keyboard,   label: "Atalhos" },
  ],
];

interface Props {
  activeItem?: string;
  onNavigate?: (id: string) => void;
}

export default function NavSidebar({ activeItem = "mode", onNavigate }: Props) {
  const { isDark } = useTheme();
  const logoSrc = isDark ? "/InolabelLogoBnraca-cropped.png" : "/inolabellogo-cropped.png";

  return (
    <aside
      style={{
        width: 260,
        minWidth: 260,
        flexShrink: 0,
        background: "var(--color-panel)",
        borderRight: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Logo */}
      <div
        style={{
          height: 80,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 16px",
          borderBottom: "1px solid var(--color-border)",
          flexShrink: 0,
        }}
      >
        <img
          src={logoSrc}
          alt="InoLabel"
          style={{
            width: 218,
            maxWidth: "100%",
            maxHeight: 54,
            height: "auto",
            objectFit: "contain",
            display: "block",
          }}
          draggable={false}
        />
      </div>

      {/* Navigation */}
      <nav
        style={{
          flex: 1,
          padding: "12px 12px 0",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi}>
            {group.map((item) => {
              const active = activeItem === item.id;
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  className={`nav-item ${active ? "nav-item-active" : ""}`}
                  onClick={() => onNavigate?.(item.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 14,
                    fontWeight: active ? 600 : 500,
                    fontFamily: "var(--font-sans)",
                    textAlign: "left",
                    marginBottom: 2,
                  }}
                >
                  <Icon
                    size={20}
                    strokeWidth={active ? 2 : 1.75}
                    style={{ flexShrink: 0 }}
                  />
                  {item.label}
                </button>
              );
            })}

            {gi < NAV_GROUPS.length - 1 && (
              <div
                style={{
                  height: 1,
                  background: "var(--color-border)",
                  margin: "8px 0",
                }}
              />
            )}
          </div>
        ))}
      </nav>

    </aside>
  );
}
