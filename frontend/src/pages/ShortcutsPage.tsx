import { Keyboard } from "lucide-react";
import PageShell from "../components/layout/PageShell";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
}

interface Shortcut {
  keys: string[];
  action: string;
}

const GROUPS: { title: string; shortcuts: Shortcut[] }[] = [
  {
    title: "Navegação de frames",
    shortcuts: [
      { keys: ["→", "D"], action: "Próximo frame" },
      { keys: ["←", "A"], action: "Frame anterior" },
      { keys: ["Shift+D"], action: "Próximo frame (segura)" },
      { keys: ["Shift+A"], action: "Frame anterior (segura)" },
    ],
  },
  {
    title: "Ferramentas de anotação",
    shortcuts: [
      { keys: ["B"], action: "Ferramenta de bounding box" },
      { keys: ["V"], action: "Ferramenta de seleção" },
      { keys: ["Ctrl+Z"], action: "Desfazer última ação" },
      { keys: ["Delete"], action: "Remover anotação selecionada" },
      { keys: ["Duplo clique"], action: "Remover anotação (no canvas)" },
    ],
  },
  {
    title: "Sessão",
    shortcuts: [
      { keys: ["Ctrl+S"], action: "Salvar frame atual" },
      { keys: ["Ctrl+E"], action: "Abrir exportação" },
      { keys: ["Ctrl+,"], action: "Configurações da sessão" },
    ],
  },
  {
    title: "Interface",
    shortcuts: [
      { keys: ["Esc"], action: "Fechar modal / cancelar operação" },
      { keys: ["?"], action: "Mostrar esta página" },
    ],
  },
];

export default function ShortcutsPage({ activeNav, onNavigate }: Props) {
  return (
    <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Atalhos">
      {/* Hero */}
      <div
        style={{
          background: "var(--color-hero-bg)",
          borderRadius: "var(--radius-xl)",
          padding: "28px 32px",
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <Keyboard size={28} color="var(--color-primary)" strokeWidth={1.75} />
          <h1 className="text-display">Atalhos de teclado</h1>
        </div>
        <p className="text-page-subtitle">
          Todos os atalhos disponíveis para agilizar o processo de anotação.
        </p>
      </div>

      {/* Groups */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {GROUPS.map((group) => (
          <div
            key={group.title}
            style={{
              background: "var(--color-panel)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 20px",
                borderBottom: "1px solid var(--color-border)",
                fontSize: 13,
                fontWeight: 700,
                color: "var(--color-text)",
                background: "var(--color-bg)",
                letterSpacing: 0,
              }}
            >
              {group.title}
            </div>
            <div style={{ padding: "8px 0" }}>
              {group.shortcuts.map((s, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "9px 20px",
                    borderBottom:
                      i < group.shortcuts.length - 1
                        ? "1px solid var(--color-border)"
                        : "none",
                  }}
                >
                  <span style={{ fontSize: 13, color: "var(--color-sidebar-text)" }}>
                    {s.action}
                  </span>
                  <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
                    {s.keys.map((key, ki) => (
                      <span key={ki} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        {ki > 0 && (
                          <span style={{ fontSize: 11, color: "var(--color-muted)" }}>ou</span>
                        )}
                        <kbd
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            justifyContent: "center",
                            minWidth: 28,
                            height: 24,
                            padding: "0 7px",
                            background: "var(--color-bg)",
                            border: "1px solid var(--color-border)",
                            borderRadius: 6,
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                            fontWeight: 600,
                            color: "var(--color-text)",
                            boxShadow: "0 1px 0 var(--color-border)",
                          }}
                        >
                          {key}
                        </kbd>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Note */}
      <div
        style={{
          marginTop: 16,
          padding: "12px 16px",
          background: "var(--color-panel)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          fontSize: 13,
          color: "var(--color-muted)",
        }}
      >
        Os atalhos ficam inativos quando o foco está em campos de texto (inputs, textareas).
      </div>
    </PageShell>
  );
}
