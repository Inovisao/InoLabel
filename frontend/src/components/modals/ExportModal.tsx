import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Download, CheckCircle, AlertCircle, Folder } from "lucide-react";
import { api } from "../../api/client";
import { useSessionStore } from "../../stores/session";

interface Props {
  open: boolean;
  onClose: () => void;
  totalFrames: number;
}

type ExportFormat = "yolo" | "coco";
type ExportState = "idle" | "running" | "done" | "error";

const FORMATS: { id: ExportFormat; label: string; desc: string; soon?: boolean }[] = [
  {
    id: "yolo",
    label: "YOLO TXT",
    desc: "Um arquivo .txt por imagem com bboxes normalizadas. Compatível com Ultralytics.",
  },
  {
    id: "coco",
    label: "COCO JSON",
    desc: "Arquivo annotations.json no formato MS COCO. Compatível com torchvision.",
    soon: true,
  },
];

export default function ExportModal({ open, onClose, totalFrames }: Props) {
  const { sessionId } = useSessionStore();

  const [format, setFormat] = useState<ExportFormat>("yolo");
  const [destination, setDestination] = useState("");
  const [name, setName] = useState("dataset_export");
  const [exportState, setExportState] = useState<ExportState>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!open) {
      setExportState("idle");
      setProgress(0);
      setErrorMsg("");
    }
  }, [open]);

  const browseDestination = async () => {
    try {
      const res = await api.get<{ path: string }>("/browse/folder");
      if (res.path) setDestination(res.path);
    } catch { /* cancelled */ }
  };

  const handleExport = async () => {
    if (!sessionId || !destination) return;
    setExportState("running");
    setProgress(0);

    try {
      const { export_id } = await api.post<{ export_id: string }>("/export", {
        session_id: sessionId,
        destination,
        name,
        formats: [format],
        split: { train: 1.0, val: 0.0, test: 0.0 },
      });

      const poll = setInterval(async () => {
        try {
          const prog = await api.get<{ progress: number; status: string; current_file: string }>(
            `/export/${export_id}/progress`
          );
          setProgress(prog.progress);
          if (prog.status === "done") {
            clearInterval(poll);
            setExportState("done");
          } else if (prog.status === "error") {
            clearInterval(poll);
            setErrorMsg(prog.current_file || "Erro desconhecido");
            setExportState("error");
          }
        } catch {
          clearInterval(poll);
          setExportState("error");
          setErrorMsg("Falha ao verificar progresso.");
        }
      }, 500);
    } catch (e) {
      setExportState("error");
      setErrorMsg((e as Error).message);
    }
  };

  const canExport = !!sessionId && !!destination.trim() && !!name.trim() && exportState === "idle";

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && exportState !== "running" && onClose()}>
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
            width: 500,
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
                {totalFrames} frames no projeto.
              </Dialog.Description>
            </div>
            <button
              className="btn-icon"
              onClick={onClose}
              disabled={exportState === "running"}
              aria-label="Fechar"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 18 }}>

            {/* Success state */}
            {exportState === "done" && (
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  padding: "16px",
                  background: "#F0FDF4",
                  border: "1px solid #86EFAC",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <CheckCircle size={20} color="#16A34A" style={{ flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#15803D" }}>
                    Dataset exportado com sucesso!
                  </div>
                  <div style={{ fontSize: 12, color: "#166534", marginTop: 2 }}>
                    Salvo em: {destination}/{name}
                  </div>
                </div>
              </div>
            )}

            {/* Error state */}
            {exportState === "error" && (
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  padding: "16px",
                  background: "#FEF2F2",
                  border: "1px solid #FECACA",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <AlertCircle size={20} color="#DC2626" style={{ flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#DC2626" }}>
                    Erro na exportação
                  </div>
                  <div style={{ fontSize: 12, color: "#991B1B", marginTop: 2 }}>{errorMsg}</div>
                </div>
              </div>
            )}

            {/* Progress bar */}
            {exportState === "running" && (
              <div>
                <div style={{ fontSize: 13, color: "var(--color-muted)", marginBottom: 8 }}>
                  Exportando… {Math.round(progress * 100)}%
                </div>
                <div
                  style={{
                    height: 6,
                    background: "var(--color-border)",
                    borderRadius: 999,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${progress * 100}%`,
                      background: "var(--color-primary)",
                      borderRadius: 999,
                      transition: "width 300ms ease",
                    }}
                  />
                </div>
              </div>
            )}

            {exportState !== "done" && (
              <>
                {/* Format */}
                <div>
                  <label className="text-label" style={{ display: "block", marginBottom: 10 }}>
                    Formato de saída
                  </label>
                  <div style={{ display: "flex", gap: 10 }}>
                    {FORMATS.map((f) => {
                      const sel = format === f.id;
                      const disabled = !!f.soon || exportState === "running";
                      return (
                        <button
                          key={f.id}
                          onClick={() => !f.soon && setFormat(f.id)}
                          disabled={disabled}
                          style={{
                            flex: 1,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "flex-start",
                            gap: 4,
                            padding: "12px 14px",
                            background: sel ? "var(--color-primary-light)" : "var(--color-bg)",
                            border: `1px solid ${sel ? "var(--color-primary)" : "var(--color-border)"}`,
                            borderRadius: "var(--radius-md)",
                            cursor: disabled ? "not-allowed" : "pointer",
                            textAlign: "left",
                            fontFamily: "var(--font-sans)",
                            opacity: f.soon ? 0.55 : 1,
                            transition: "background 150ms, border-color 150ms",
                          }}
                        >
                          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: sel ? "var(--color-primary)" : "var(--color-text)" }}>
                              {f.label}
                            </span>
                            {f.soon && (
                              <span style={{ fontSize: 10, fontWeight: 600, color: "#92400E", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 4, padding: "1px 5px" }}>
                                em breve
                              </span>
                            )}
                          </span>
                          <span style={{ fontSize: 11, color: "var(--color-muted)", lineHeight: 1.4 }}>
                            {f.desc}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Destination */}
                <div>
                  <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
                    Pasta de destino
                  </label>
                  <span className="text-helper" style={{ display: "block", marginBottom: 6 }}>
                    Onde salvar os arquivos exportados.
                  </span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      className="input"
                      style={{ flex: 1 }}
                      placeholder="/caminho/para/exportar"
                      value={destination}
                      disabled={exportState === "running"}
                      onChange={(e) => setDestination(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={browseDestination}
                      disabled={exportState === "running"}
                      title="Selecionar pasta"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 40,
                        height: 40,
                        flexShrink: 0,
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                        background: "var(--color-panel)",
                        cursor: "pointer",
                        color: "var(--color-primary)",
                      }}
                    >
                      <Folder size={17} strokeWidth={1.75} />
                    </button>
                  </div>
                </div>

                {/* Dataset name */}
                <div>
                  <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
                    Nome do dataset
                  </label>
                  <input
                    className="input"
                    placeholder="dataset_export"
                    value={name}
                    disabled={exportState === "running"}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div
            style={{
              padding: "16px 28px 24px",
              display: "flex",
              justifyContent: "flex-end",
              gap: 10,
              borderTop: "1px solid var(--color-border)",
            }}
          >
            <button
              className="btn-secondary"
              onClick={onClose}
              disabled={exportState === "running"}
            >
              {exportState === "done" ? "Fechar" : "Cancelar"}
            </button>
            {exportState !== "done" && (
              <button
                className="btn-primary"
                onClick={handleExport}
                disabled={!canExport}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  opacity: canExport ? 1 : 0.5,
                  cursor: canExport ? "pointer" : "not-allowed",
                }}
              >
                <Download size={16} />
                {exportState === "running" ? "Exportando…" : `Exportar ${format.toUpperCase()}`}
              </button>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
