import {
  LayoutGrid, Database, Settings, Folder,
  History, HelpCircle, Keyboard,
} from "lucide-react";

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
          padding: "0 20px",
          borderBottom: "1px solid var(--color-border)",
          flexShrink: 0,
        }}
      >
        <img
          src="/inolabellogo.png"
          alt="InoLabel"
          style={{ height: 75, width: "auto", objectFit: "contain" }}
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
                    background: active ? "var(--color-primary-light)" : "transparent",
                    color: active ? "var(--color-primary)" : "var(--color-sidebar-text)",
                    fontSize: 14,
                    fontWeight: active ? 600 : 500,
                    fontFamily: "var(--font-sans)",
                    textAlign: "left",
                    transition: "background 120ms, color 120ms",
                    marginBottom: 2,
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      (e.currentTarget as HTMLButtonElement).style.background = "#F9FAFB";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                    }
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
