import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Download, CheckCircle, AlertCircle, Folder } from "lucide-react";
import { api } from "../../api/client";
import type { AugmentationOption, ExportProgress } from "../../api/types";
import { useSessionStore } from "../../stores/session";

interface Props {
  open: boolean;
  onClose: () => void;
  totalFrames: number;
}

type ExportFormat = "yolo" | "coco";
type ExportState = "idle" | "running" | "done" | "error";

type CocoLayout = "roboflow" | "images_dir";

const FORMATS: { id: ExportFormat; label: string; desc: string }[] = [
  {
    id: "yolo",
    label: "YOLO TXT",
    desc: "Um arquivo .txt por imagem com bboxes normalizadas. Compatível com Ultralytics.",
  },
  {
    id: "coco",
    label: "COCO JSON",
    desc: "Arquivo _annotations.coco.json no formato MS COCO. Compatível com torchvision.",
  },
];

interface SplitValues {
  train: number;
  val: number;
  test: number;
}

const DEFAULT_SPLIT: SplitValues = { train: 70, val: 20, test: 10 };

function SplitRow({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span
        style={{
          width: 36,
          fontSize: 12,
          fontWeight: 600,
          color: "var(--color-muted)",
          textAlign: "right",
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, accentColor: "var(--color-primary)", cursor: disabled ? "not-allowed" : "pointer" }}
      />
      <span
        style={{
          width: 38,
          fontSize: 12,
          fontWeight: 600,
          color: "var(--color-text)",
          textAlign: "right",
          flexShrink: 0,
        }}
      >
        {value}%
      </span>
    </div>
  );
}

export default function ExportModal({ open, onClose, totalFrames }: Props) {
  const { sessionId, outputPath, mode } = useSessionStore();
  const isKeypoint = mode === "keypoint";

  const [formats, setFormats] = useState<ExportFormat[]>(["yolo", "coco"]);
  const [cocoLayout, setCocoLayout] = useState<CocoLayout>("roboflow");
  const [augment, setAugment] = useState(false);
  const [augCatalog, setAugCatalog] = useState<AugmentationOption[]>([]);
  // Keypoint: espelhar não troca os nomes dos pontos (esquerda vira direita), então fica fora do padrão.
  const [augKeys, setAugKeys] = useState<string[]>(
    mode === "keypoint" ? ["brightness", "contrast"] : ["flip_h", "brightness", "contrast"]
  );
  const [augCopies, setAugCopies] = useState(1);
  const [destination, setDestination] = useState("");
  const [name, setName] = useState("dataset_export");
  const [exportState, setExportState] = useState<ExportState>("idle");
  const [progress, setProgress] = useState(0);
  const [currentFile, setCurrentFile] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [useSplit, setUseSplit] = useState(false);
  const [split, setSplit] = useState<SplitValues>(DEFAULT_SPLIT);
  const [zipOutput, setZipOutput] = useState(true);
  const [zipPath, setZipPath] = useState("");

  useEffect(() => {
    if (!open) {
      setExportState("idle");
      setProgress(0);
      setCurrentFile("");
      setErrorMsg("");
      setZipPath("");
    }
  }, [open]);

  // Destino padrão: <pasta do projeto>/exports.
  useEffect(() => {
    if (open && !destination && outputPath) {
      setDestination(`${outputPath.replace(/[\\/]+$/, "")}/exports`);
    }
  }, [open, outputPath]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!open || augCatalog.length) return;
    api.get<AugmentationOption[]>("/export/augmentations").then(setAugCatalog).catch(() => setAugCatalog([]));
  }, [open, augCatalog.length]);

  const toggleFormat = (id: ExportFormat) =>
    setFormats((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]));

  const toggleAug = (key: string) =>
    setAugKeys((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));

  const splitTotal = split.train + split.val + split.test;
  const splitValid = Math.abs(splitTotal - 100) <= 1;

  const adjustSplit = (key: keyof SplitValues, value: number) => {
    setSplit((prev) => {
      const next = { ...prev, [key]: value };
      const others = (["train", "val", "test"] as (keyof SplitValues)[]).filter((k) => k !== key);
      const remaining = 100 - value;
      const prevOthersTotal = others.reduce((s, k) => s + prev[k], 0);
      if (prevOthersTotal === 0) {
        const each = Math.round(remaining / 2);
        others.forEach((k, i) => { next[k] = i === 0 ? each : remaining - each; });
      } else {
        others.forEach((k) => {
          next[k] = Math.round((prev[k] / prevOthersTotal) * remaining);
        });
        const diff = 100 - Object.values(next).reduce((s, v) => s + v, 0);
        next[others[0]] += diff;
      }
      return next;
    });
  };

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
    setCurrentFile("");
    setZipPath("");

    const splitPayload = useSplit
      ? { train: split.train / 100, val: split.val / 100, test: split.test / 100 }
      : { train: 1.0, val: 0.0, test: 0.0 };

    try {
      const { export_id } = await api.post<{ export_id: string }>("/export", {
        session_id: sessionId,
        destination,
        name,
        formats,
        use_split: useSplit,
        split: splitPayload,
        zip: zipOutput,
        coco_layout: cocoLayout,
        augmentation: augment,
        augmentations: augment ? augKeys : [],
        augmentation_copies: augCopies,
      });

      const poll = setInterval(async () => {
        try {
          const prog = await api.get<ExportProgress>(`/export/${export_id}/progress`);
          setProgress(prog.progress);
          if (prog.current_file) setCurrentFile(prog.current_file);
          if (prog.status === "done") {
            clearInterval(poll);
            setZipPath(prog.zip_path ?? "");
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

  const canExport =
    !!sessionId &&
    !!destination.trim() &&
    !!name.trim() &&
    formats.length > 0 &&
    (!augment || augKeys.length > 0) &&
    exportState === "idle" &&
    (!useSplit || splitValid);

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && exportState !== "running" && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content
          className="modal-content"
          style={{
            width: 500,
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
              <div className="alert alert-success">
                <CheckCircle size={20} color="var(--alert-icon)" style={{ flexShrink: 0 }} />
                <div>
                  <div className="alert-title">
                    Dataset exportado com sucesso!
                  </div>
                  <div className="alert-text">
                    Salvo em: {destination}/{name}
                  </div>
                  {zipPath && (
                    <div className="alert-text">
                      Pacote zipado: {zipPath}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error state */}
            {exportState === "error" && (
              <div className="alert alert-error">
                <AlertCircle size={20} color="var(--alert-icon)" style={{ flexShrink: 0 }} />
                <div>
                  <div className="alert-title">
                    Erro na exportação
                  </div>
                  <div className="alert-text">{errorMsg}</div>
                </div>
              </div>
            )}

            {/* Progress bar */}
            {exportState === "running" && (
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    color: "var(--color-muted)",
                    marginBottom: 6,
                  }}
                >
                  <span>{currentFile || "Exportando…"}</span>
                  <span>{Math.round(progress * 100)}%</span>
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
                      transition: "width var(--motion-slow)",
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
                    Formatos de saída
                  </label>
                  <div style={{ display: "flex", gap: 10 }}>
                    {FORMATS.map((f) => {
                      const sel = formats.includes(f.id);
                      const disabled = exportState === "running";
                      return (
                        <button
                          key={f.id}
                          onClick={() => toggleFormat(f.id)}
                          disabled={disabled}
                          aria-pressed={sel}
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
                            transition: "background var(--motion-base), border-color var(--motion-base)",
                          }}
                        >
                          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: sel ? "var(--color-primary)" : "var(--color-text)" }}>
                              {isKeypoint ? (f.id === "yolo" ? "YOLO Pose" : "COCO Keypoints") : f.label}
                            </span>
                            {sel && <CheckCircle size={13} color="var(--color-primary)" />}
                          </span>
                          <span style={{ fontSize: 11, color: "var(--color-muted)", lineHeight: 1.4 }}>
                            {f.desc}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {formats.includes("coco") && (
                  <div>
                    <label className="text-label" style={{ display: "block", marginBottom: 6 }}>
                      Organização do COCO
                    </label>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {([
                        ["roboflow", "Estilo Roboflow", "train/_annotations.coco.json com as imagens na mesma pasta."],
                        ["images_dir", "Pasta images/", "_annotations.coco.json com as imagens em images/."],
                      ] as [CocoLayout, string, string][]).map(([id, label, desc]) => (
                        <label key={id} style={{ display: "flex", gap: 8, alignItems: "flex-start", cursor: "pointer", fontSize: 13 }}>
                          <input
                            type="radio"
                            name="coco-layout"
                            checked={cocoLayout === id}
                            disabled={exportState === "running"}
                            onChange={() => setCocoLayout(id)}
                            style={{ accentColor: "var(--color-primary)", marginTop: 3 }}
                          />
                          <span>
                            <strong>{label}</strong>{" "}
                            <span style={{ color: "var(--color-muted)", fontSize: 12 }}>— {desc}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {/* Destination */}
                <div>
                  <label className="text-label" style={{ display: "block", marginBottom: 4 }}>
                    Pasta de destino
                  </label>
                  <span className="text-helper" style={{ display: "block", marginBottom: 6 }}>
                    Por padrão, a pasta exports/ dentro do projeto.
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
                      className="btn-icon"
                      type="button"
                      onClick={browseDestination}
                      disabled={exportState === "running"}
                      title="Selecionar pasta"
                      style={{
                        width: 40,
                        height: 40,
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

                {/* Split config */}
                <div>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: exportState === "running" ? "not-allowed" : "pointer",
                      userSelect: "none",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={useSplit}
                      disabled={exportState === "running"}
                      onChange={(e) => {
                        setUseSplit(e.target.checked);
                        if (!e.target.checked) setAugment(false);
                      }}
                      style={{ accentColor: "var(--color-primary)", width: 14, height: 14, cursor: "inherit" }}
                    />
                    <span className="text-label">Dividir em train / val / test</span>
                  </label>

                  {useSplit && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: "14px 16px",
                        background: "var(--color-bg)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 10,
                      }}
                    >
                      <SplitRow
                        label="Train"
                        value={split.train}
                        onChange={(v) => adjustSplit("train", v)}
                        disabled={exportState === "running"}
                      />
                      <SplitRow
                        label="Val"
                        value={split.val}
                        onChange={(v) => adjustSplit("val", v)}
                        disabled={exportState === "running"}
                      />
                      <SplitRow
                        label="Test"
                        value={split.test}
                        onChange={(v) => adjustSplit("test", v)}
                        disabled={exportState === "running"}
                      />
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "flex-end",
                          fontSize: 11,
                          color: splitValid ? "var(--color-muted)" : "var(--color-danger)",
                          marginTop: 2,
                        }}
                      >
                        Total: {splitTotal}% {!splitValid && "— deve somar 100%"}
                      </div>
                    </div>
                  )}
                </div>

                {/* Augmentation */}
                <div>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: exportState === "running" ? "not-allowed" : "pointer",
                      userSelect: "none",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={augment}
                      disabled={exportState === "running"}
                      onChange={(e) => {
                        setAugment(e.target.checked);
                        // Cópias aumentadas só entram no treino; sem divisão não haveria treino.
                        if (e.target.checked) setUseSplit(true);
                      }}
                      style={{ accentColor: "var(--color-primary)", width: 14, height: 14, cursor: "inherit" }}
                    />
                    <span className="text-label">Gerar imagens aumentadas (augmentation)</span>
                  </label>
                  {augment && (
                    <div
                      style={{
                        marginTop: 10,
                        padding: "12px 14px",
                        background: "var(--color-bg)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {augCatalog.map((a) => {
                          const on = augKeys.includes(a.key);
                          return (
                            <button
                              key={a.key}
                              type="button"
                              title={a.description}
                              aria-pressed={on}
                              disabled={exportState === "running"}
                              onClick={() => toggleAug(a.key)}
                              style={{
                                fontSize: 12,
                                padding: "4px 10px",
                                borderRadius: 999,
                                border: `1px solid ${on ? "var(--color-primary)" : "var(--color-border)"}`,
                                background: on ? "var(--color-primary-light)" : "var(--color-panel)",
                                color: on ? "var(--color-primary)" : "var(--color-text)",
                                cursor: "pointer",
                                fontFamily: "var(--font-sans)",
                              }}
                            >
                              {a.label}
                            </button>
                          );
                        })}
                        {augCatalog.length === 0 && (
                          <span className="text-helper">Catálogo de augmentation indisponível.</span>
                        )}
                      </div>
                      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                        Cópias por imagem
                        <select
                          className="input"
                          value={augCopies}
                          disabled={exportState === "running"}
                          onChange={(e) => setAugCopies(Number(e.target.value))}
                          style={{ width: 70, height: 30, fontSize: 12 }}
                        >
                          {[1, 2, 3, 4, 5].map((n) => (
                            <option key={n} value={n}>{n}</option>
                          ))}
                        </select>
                      </label>
                      {isKeypoint && augKeys.some((k) => k.startsWith("flip")) && (
                        <span className="text-helper" style={{ color: "var(--color-warning)" }}>
                          Espelhar não troca os nomes dos pontos: um ponto "esquerdo" passa a ficar à direita.
                        </span>
                      )}
                      <span className="text-helper">
                        Só nas imagens de treino do YOLO (val/test e COCO ficam sem cópias, para não vazar dados na validação).
                      </span>
                    </div>
                  )}
                </div>

                {/* Zip package */}
                <div>
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: exportState === "running" ? "not-allowed" : "pointer",
                      userSelect: "none",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={zipOutput}
                      disabled={exportState === "running"}
                      onChange={(e) => setZipOutput(e.target.checked)}
                      style={{ accentColor: "var(--color-primary)", width: 14, height: 14, cursor: "inherit" }}
                    />
                    <span className="text-label">Gerar também um pacote .zip</span>
                  </label>
                  <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 4, marginLeft: 22 }}>
                    Imagens e anotações juntas em {name || "dataset"}.zip, com as referências conferidas.
                  </div>
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
                {exportState === "running"
                  ? "Exportando…"
                  : `Exportar ${formats.map((f) => f.toUpperCase()).join(" + ") || ""}`}
              </button>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
