import * as Dialog from "@radix-ui/react-dialog";
import { X, LogOut } from "lucide-react";
import { useSessionStore } from "../../stores/session";
import { useAnnotationStore } from "../../stores/annotation";

const MODE_LABELS: Record<string, string> = {
  tracking: "Rastreamento",
  detection: "Detecção padrão",
  obb: "Detecção orientada (OBB)",
  classification: "Classificação",
};

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function SettingsModal({ open, onClose }: Props) {
  const { mode, classes, stop } = useSessionStore();
  const { classes: classItems } = useAnnotationStore();

  const handleStop = async () => {
    onClose();
    await stop();
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.35)",
            zIndex: 1000,
            backdropFilter: "blur(2px)",
          }}
        />
        <Dialog.Content
          style={{
            position: "fixed",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 1001,
            width: 460,
            background: "var(--color-panel)",
            borderRadius: "var(--radius-xl)",
            boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
            fontFamily: "var(--font-sans)",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "24px 28px 20px",
              borderBottom: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Dialog.Title
                style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 4 }}
              >
                Sessão atual
              </Dialog.Title>
              <Dialog.Description style={{ fontSize: 13, color: "var(--color-muted)" }}>
                Configurações da sessão de anotação em andamento.
              </Dialog.Description>
            </div>
            <button className="btn-icon" onClick={onClose} aria-label="Fechar">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 16 }}>
            <ConfigRow label="Modo" value={mode ? (MODE_LABELS[mode] ?? mode) : "—"} />

            {/* Classes */}
            <div>
              <div className="text-label" style={{ marginBottom: 8 }}>
                Classes ({classItems.length})
              </div>
              {classItems.length > 0 ? (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {classItems.map((cls) => (
                    <span
                      key={cls.id}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 10px 4px 8px",
                        background: "var(--color-bg)",
                        border: "1px solid var(--color-border)",
                        borderRadius: 999,
                        fontSize: 13,
                        color: "var(--color-sidebar-text)",
                      }}
                    >
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          background: cls.color ?? "var(--color-primary)",
                          flexShrink: 0,
                        }}
                      />
                      {cls.name}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-helper">Nenhuma classe configurada.</span>
              )}
            </div>

            {/* Nota de alteração */}
            <div
              style={{
                padding: "12px 14px",
                background: "var(--color-hero-bg)",
                borderRadius: "var(--radius-md)",
                fontSize: 13,
                color: "var(--color-muted)",
                lineHeight: 1.5,
              }}
            >
              Para alterar o modo ou as classes, encerre a sessão atual e inicie uma nova
              pelo wizard.
            </div>
          </div>

          {/* Footer */}
          <div
            style={{
              padding: "16px 28px 24px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderTop: "1px solid var(--color-border)",
            }}
          >
            <button
              onClick={handleStop}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                height: 40,
                padding: "0 16px",
                background: "transparent",
                border: "1px solid #FECACA",
                borderRadius: "var(--radius-md)",
                color: "var(--color-danger)",
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                transition: "background 150ms",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.background = "#FEF2F2")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.background = "transparent")
              }
            >
              <LogOut size={15} />
              Encerrar sessão
            </button>
            <button className="btn-secondary" onClick={onClose} style={{ height: 40, fontSize: 14 }}>
              Fechar
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <span className="text-label" style={{ fontWeight: 500, color: "var(--color-muted)" }}>
        {label}
      </span>
      <span
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: "var(--color-text)",
          background: "var(--color-bg)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-sm)",
          padding: "3px 10px",
        }}
      >
        {value}
      </span>
    </div>
  );
}
