import * as Dialog from "@radix-ui/react-dialog";
import { Download, X } from "lucide-react";
import { useSessionStore } from "../../shared/session/store";
import AugmentationSection from "./sections/AugmentationSection";
import CocoLayoutSection from "./sections/CocoLayoutSection";
import DestinationSection from "./sections/DestinationSection";
import ExportStatus from "./sections/ExportStatus";
import FormatSection from "./sections/FormatSection";
import SplitSection from "./sections/SplitSection";
import ZipSection from "./sections/ZipSection";
import { useExportJob } from "./useExportJob";
import { useExportOptions } from "./useExportOptions";

interface Props {
  open: boolean;
  onClose: () => void;
  totalFrames: number;
}

/** Exportar o dataset do projeto: formatos, destino, divisão, augmentation e .zip. */
export default function ExportModal({ open, onClose, totalFrames }: Props) {
  const { sessionId, outputPath, mode } = useSessionStore();
  const options = useExportOptions(open, mode, outputPath);
  const job = useExportJob(open);
  const running = job.state === "running";
  const canExport = !!sessionId && options.isValid && job.state === "idle";

  const handleExport = () => {
    if (!sessionId || !options.destination) return;
    job.start({ session_id: sessionId, ...options.requestBody() });
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && !running && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="modal-overlay" />
        <Dialog.Content className="modal-content" style={{ width: 500 }}>
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
              <Dialog.Title style={{ fontSize: 18, fontWeight: 700, color: "var(--color-text)", marginBottom: 4 }}>
                Exportar dataset
              </Dialog.Title>
              <Dialog.Description style={{ fontSize: 13, color: "var(--color-muted)" }}>
                {totalFrames} frames no projeto.
              </Dialog.Description>
            </div>
            <button className="btn-icon" onClick={onClose} disabled={running} aria-label="Fechar">
              <X size={16} />
            </button>
          </div>

          <div style={{ padding: "20px 28px", display: "flex", flexDirection: "column", gap: 18 }}>
            <ExportStatus
              state={job.state}
              progress={job.progress}
              currentFile={job.currentFile}
              errorMsg={job.errorMsg}
              savedAt={`${options.destination}/${options.name}`}
              zipPath={job.zipPath}
            />

            {job.state !== "done" && (
              <>
                <FormatSection
                  selected={options.formats}
                  onToggle={options.toggleFormat}
                  isKeypoint={mode === "keypoint"}
                  disabled={running}
                />
                {options.formats.includes("coco") && (
                  <CocoLayoutSection value={options.cocoLayout} onChange={options.setCocoLayout} disabled={running} />
                )}
                <DestinationSection
                  destination={options.destination}
                  onDestination={options.setDestination}
                  name={options.name}
                  onName={options.setName}
                  disabled={running}
                />
                <SplitSection
                  enabled={options.useSplit}
                  onEnabled={options.setUseSplit}
                  split={options.split}
                  onAdjust={options.adjustSplit}
                  disabled={running}
                />
                <AugmentationSection
                  enabled={options.augment}
                  onEnabled={options.setAugment}
                  catalog={options.augCatalog}
                  selected={options.augKeys}
                  onToggle={options.toggleAug}
                  copies={options.augCopies}
                  onCopies={options.setAugCopies}
                  isKeypoint={mode === "keypoint"}
                  disabled={running}
                />
                <ZipSection
                  enabled={options.zipOutput}
                  onEnabled={options.setZipOutput}
                  datasetName={options.name}
                  disabled={running}
                />
              </>
            )}
          </div>

          <div
            style={{
              padding: "16px 28px 24px",
              display: "flex",
              justifyContent: "flex-end",
              gap: 10,
              borderTop: "1px solid var(--color-border)",
            }}
          >
            <button className="btn-secondary" onClick={onClose} disabled={running}>
              {job.state === "done" ? "Fechar" : "Cancelar"}
            </button>
            {job.state !== "done" && (
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
                {running ? "Exportando…" : `Exportar ${options.formats.map((f) => f.toUpperCase()).join(" + ") || ""}`}
              </button>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
