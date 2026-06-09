import { useAnnotationStore } from "../../stores/annotation";

export default function Sidebar() {
  const { classes, selectedClassId, setSelectedClass } = useAnnotationStore();

  return (
    <aside
      style={{
        width: 240,
        minWidth: 200,
        maxWidth: 280,
        flexShrink: 0,
        background: "var(--color-panel)",
        borderRight: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div className="sidebar-label">Classes</div>

      <div
        style={{
          padding: "0 8px",
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        {classes.map((cls) => {
          const active = selectedClassId === cls.id;
          return (
            <button
              key={cls.id}
              className={`nav-item ${active ? "nav-item-active" : ""}`}
              onClick={() => setSelectedClass(cls.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                minHeight: 36,
                padding: "7px 10px",
                border: "1px solid transparent",
                borderRadius: "var(--radius-md)",
                cursor: "pointer",
                textAlign: "left",
                width: "100%",
                fontFamily: "var(--font-sans)",
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 3,
                  background: cls.color ?? "var(--color-primary)",
                  flexShrink: 0,
                  boxShadow: active
                    ? `0 0 0 2px var(--color-panel), 0 0 0 3px ${cls.color ?? "var(--color-primary)"}`
                    : "none",
                  transition: "box-shadow 120ms",
                }}
              />
              <span
                style={{
                  fontSize: 13,
                  fontWeight: active ? 600 : 400,
                  color: active ? "var(--color-primary)" : "var(--color-sidebar-text)",
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {cls.name}
              </span>
              <span
                className="text-mono"
                style={{ fontSize: 10, color: "var(--color-muted)", flexShrink: 0 }}
              >
                {cls.id}
              </span>
            </button>
          );
        })}

        {classes.length === 0 && (
          <p className="text-helper" style={{ padding: "8px 10px", fontStyle: "italic" }}>
            Nenhuma classe carregada.
          </p>
        )}
      </div>

      <div className="divider" />
      <div className="sidebar-label">Ferramentas</div>

      <div style={{ padding: "0 8px 12px", display: "flex", flexDirection: "column", gap: 2 }}>
        <ToolButton label="Caixa delimitadora" shortcut="B" />
        <ToolButton label="Mover / selecionar" shortcut="V" />
        <ToolButton label="Desfazer" shortcut="Ctrl+Z" />
      </div>
    </aside>
  );
}

function ToolButton({ label, shortcut }: { label: string; shortcut: string }) {
  return (
    <div
      className="nav-item"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 10px",
        borderRadius: "var(--radius-md)",
        cursor: "pointer",
        fontSize: 13,
      }}
    >
      <span>{label}</span>
      <span
        style={{
          fontSize: 10,
          fontFamily: "var(--font-mono)",
          color: "var(--color-muted)",
          background: "var(--color-neutral)",
          border: "1px solid var(--color-border)",
          borderRadius: 4,
          padding: "1px 5px",
        }}
      >
        {shortcut}
      </span>
    </div>
  );
}
