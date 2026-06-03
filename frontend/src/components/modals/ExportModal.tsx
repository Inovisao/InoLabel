import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Download, Construction } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  totalFrames: number;
  annotatedCount?: number;
}

type ExportFormat = "yolo" | "coco";

const FORMATS: { id: ExportFormat; label: string; desc: string }[] = [
  {
    id: "yolo",
    label: "YOLO TXT",
    desc: "Um arquivo .txt por imagem com bboxes normalizadas. Compatível com Ultralytics.",
  },
  {
    id: "coco",
    label: "COCO JSON",
    desc: "Arquivo annotations.json único no formato MS COCO. Compatível com torchvision.",
  },
];

export default function ExportModal({ open, onClose, totalFrames, annotatedCount }: Props) {
  const [format, setFormat] = useState<ExportFormat>("yolo");

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
            width: 480,
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
                Exportar dataset
              </Dialog.Title>
              <Dialog.Description style={{ fontSize: 13, color: "var(--color-muted)" }}>
                {annotatedCount !== undefined
                  ? `${annotatedCount} frames anotados de ${totalFrames} no total.`
                  : `${totalFrames} frames no projeto.`}
              </Dialog.Description>
            </div>
            <button className="btn-icon" onClick={onClose} aria-label="Fechar">
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div style={{ padding: "20px 28px" }}>
            {/* Em desenvolvimento notice */}
            <div
              style={{
                display: "flex",
                gap: 12,
                padding: "14px 16px",
                background: "#FFFBEB",
                border: "1px solid #FDE68A",
                borderRadius: "var(--radius-md)",
                marginBottom: 20,
              }}
            >
              <Construction size={18} color="#F59E0B" style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#92400E", marginBottom: 2 }}>
                  Funcionalidade em desenvolvimento
                </div>
                <div style={{ fontSize: 12, color: "#B45309", lineHeight: 1.5 }}>
                  A exportação ainda está sendo implementada no backend. Você poderá
                  usar esta janela em breve para gerar os arquivos do dataset.
                </div>
              </div>
            </div>

            {/* Format selector */}
            <label className="text-label" style={{ display: "block", marginBottom: 12 }}>
              Formato de saída
            </label>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {FORMATS.map((f) => {
                const sel = format === f.id;
                return (
                  <button
                    key={f.id}
                    onClick={() => setFormat(f.id)}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                      padding: "14px 16px",
                      background: sel ? "var(--color-primary-light)" : "var(--color-bg)",
                      border: `1px solid ${sel ? "var(--color-primary)" : "var(--color-border)"}`,
                      borderRadius: "var(--radius-md)",
                      cursor: "pointer",
                      textAlign: "left",
                      fontFamily: "var(--font-sans)",
                      transition: "background 150ms, border-color 150ms",
                    }}
                  >
                    <div
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: "50%",
                        border: `2px solid ${sel ? "var(--color-primary)" : "#D1D5DB"}`,
                        background: sel ? "var(--color-primary)" : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        marginTop: 2,
                      }}
                    >
                      {sel && <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#fff" }} />}
                    </div>
                    <div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: sel ? "var(--color-primary)" : "var(--color-text)",
                          marginBottom: 3,
                        }}
                      >
                        {f.label}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--color-muted)", lineHeight: 1.5 }}>
                        {f.desc}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div
            style={{
              padding: "16px 28px 24px",
              display: "flex",
              justifyContent: "flex-end",
              gap: 10,
            }}
          >
            <button className="btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button
              className="btn-primary"
              disabled
              style={{ opacity: 0.45, cursor: "not-allowed" }}
            >
              <Download size={16} />
              Exportar {format.toUpperCase()}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
