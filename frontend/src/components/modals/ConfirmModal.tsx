import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle } from "lucide-react";

interface Props {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = "Confirmar",
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onCancel()}>
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
            width: 420,
            background: "var(--color-panel)",
            borderRadius: "var(--radius-xl)",
            padding: 28,
            boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
            fontFamily: "var(--font-sans)",
          }}
        >
          <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: danger ? "#FEF2F2" : "var(--color-hero-bg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <AlertTriangle
                size={22}
                color={danger ? "#EF4444" : "var(--color-primary)"}
                strokeWidth={2}
              />
            </div>
            <div>
              <Dialog.Title
                style={{
                  fontSize: 16,
                  fontWeight: 700,
                  color: "var(--color-text)",
                  marginBottom: 4,
                }}
              >
                {title}
              </Dialog.Title>
              <Dialog.Description
                style={{ fontSize: 14, color: "var(--color-muted)", lineHeight: 1.5 }}
              >
                {description}
              </Dialog.Description>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button className="btn-secondary" onClick={onCancel}>
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                height: 48,
                padding: "0 20px",
                borderRadius: "var(--radius-md)",
                fontSize: 15,
                fontWeight: 600,
                cursor: "pointer",
                border: "1px solid transparent",
                background: danger ? "var(--color-danger)" : "var(--color-primary)",
                color: "#fff",
                fontFamily: "var(--font-sans)",
              }}
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
