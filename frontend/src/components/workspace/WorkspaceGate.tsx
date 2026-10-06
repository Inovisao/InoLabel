import { useState } from "react";
import { FolderOpen, Clock, AlertCircle } from "lucide-react";
import { api } from "../../api/client";
import { useWorkspaceStore } from "../../stores/workspace";

/**
 * Primeira tela quando não há workspace: escolher a pasta onde os projetos ficam,
 * como os vaults do Obsidian. Cada projeto vira uma subpasta dela.
 */
export default function WorkspaceGate() {
  const { recent, open, error } = useWorkspaceStore();
  const [busy, setBusy] = useState(false);

  const choose = async () => {
    try {
      const res = await api.get<{ path: string }>("/browse/folder");
      if (!res.path) return;
      setBusy(true);
      await open(res.path);
    } finally {
      setBusy(false);
    }
  };

  const reopen = async (path: string) => {
    setBusy(true);
    try {
      await open(path);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-bg)",
        padding: "32px 16px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          background: "var(--color-panel)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: 28,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22, color: "var(--color-text)" }}>Escolha o workspace</h1>
          <p className="text-helper" style={{ marginTop: 6 }}>
            O workspace é a pasta onde o InoLabel guarda todos os seus projetos. Cada projeto vira uma
            subpasta dela, com as anotações e as exportações. Pode ser uma pasta nova ou uma que já tenha
            projetos.
          </p>
        </div>

        <button className="btn-primary" onClick={choose} disabled={busy} style={{ alignSelf: "flex-start" }}>
          <FolderOpen size={16} /> Escolher pasta do workspace
        </button>

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={18} color="var(--alert-icon)" style={{ flexShrink: 0 }} />
            <div className="alert-text">{error}</div>
          </div>
        )}

        {recent.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="sidebar-label" style={{ padding: 0 }}>Recentes</div>
            {recent.map((item) => (
              <button
                key={item.path}
                className="nav-item"
                disabled={!item.exists || busy}
                onClick={() => reopen(item.path)}
                title={item.exists ? item.path : "Pasta não encontrada"}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 10px",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  background: "var(--color-panel)",
                  cursor: item.exists ? "pointer" : "not-allowed",
                  textAlign: "left",
                  opacity: item.exists ? 1 : 0.55,
                }}
              >
                <Clock size={14} color="var(--color-muted)" />
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: "block", fontWeight: 600, color: "var(--color-text)" }}>{item.name}</span>
                  <span className="text-mono" style={{ display: "block", fontSize: 11, color: "var(--color-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.exists ? item.path : `${item.path} (não encontrada)`}
                  </span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
