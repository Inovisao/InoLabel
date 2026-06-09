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
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content
          className="modal-content"
          style={{
            width: 420,
            padding: 28,
          }}
        >
          <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: danger ? "var(--color-error-bg)" : "var(--color-hero-bg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <AlertTriangle
                size={22}
                color={danger ? "var(--color-error-icon)" : "var(--color-primary)"}
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
              className={danger ? "btn-danger" : "btn-primary"}
              onClick={onConfirm}
              style={{
                minWidth: 112,
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
