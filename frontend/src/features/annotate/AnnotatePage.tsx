import { useEffect, useState } from "react";
import NavSidebar from "../../shared/layout/NavSidebar";
import Topbar from "./Topbar";
import Sidebar from "./sidebar/Sidebar";
import Statusbar from "./Statusbar";
import AnnotationCanvas from "./canvas/AnnotationCanvas";
import ExportModal from "../export/ExportModal";
import SettingsModal from "./SettingsModal";
import ConfirmModal from "../../shared/ui/ConfirmModal";
import { useAnnotationStore } from "./store";
import { useSessionStore } from "../../shared/session/store";
import { useKeyboardShortcuts } from "./useKeyboardShortcuts";
import AutolabelingPanel from "../autolabeling/AutolabelingPanel";
import { useAutolabeling } from "../autolabeling/useAutolabeling";
import { useAutolabelingStore } from "../autolabeling/store";
import { useToast } from "../../shared/ui/ToastContext";

interface Props {
  onStop?: (dest?: string) => void;
}

export default function AnnotatePage({ onStop }: Props) {
  const { fetchFrame, fetchClasses, resetSessionUi } = useAnnotationStore();
  const totalFrames = useSessionStore((s) => s.totalFrames);
  const { stop } = useSessionStore();
  const { toast } = useToast();

  useAutolabeling();
  const [autolabelOpen, setAutolabelOpen] = useState(false);
  const [autolabelWorkspace, setAutolabelWorkspace] = useState(false);
  const running = useAutolabelingStore((s) => s.runs.some((r) => r.status === "running" || r.status === "queued"));

  const [exportOpen, setExportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmStopOpen, setConfirmStopOpen] = useState(false);
  const [pendingNav, setPendingNav] = useState<string | undefined>(undefined);

  useEffect(() => {
    resetSessionUi();
    fetchClasses();
    fetchFrame();
  }, [fetchClasses, fetchFrame, resetSessionUi]);

  useKeyboardShortcuts({
    onExport: () => setExportOpen(true),
    onSettings: () => setSettingsOpen(true),
    onSave: () => toast("Anotações salvas automaticamente a cada operação.", "success"),
  });

  const handleNavRequest = (id: string) => {
    if (id === "autolabeling") { setAutolabelWorkspace(true); return; }
    if (id === "mode" && autolabelWorkspace) { setAutolabelWorkspace(false); return; }
    setPendingNav(id);
    setConfirmStopOpen(true);
  };

  const handleStopConfirm = async () => {
    setConfirmStopOpen(false);
    await stop();
    onStop?.(pendingNav);
  };

  const handleTopbarStop = () => {
    setPendingNav(undefined);
    setConfirmStopOpen(true);
  };

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <NavSidebar activeItem={autolabelWorkspace ? "autolabeling" : "mode"} onNavigate={handleNavRequest} />

      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          minWidth: 0,
        }}
      >
        <Topbar
          autolabelingOpen={autolabelOpen || autolabelWorkspace}
          onAutolabeling={() => { setAutolabelWorkspace(false); setAutolabelOpen((open) => !open); }}
          onExport={() => setExportOpen(true)}
          onSettings={() => setSettingsOpen(true)}
          onStop={handleTopbarStop}
        />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {autolabelWorkspace ? <AutolabelingPanel workspace onReview={() => { setAutolabelWorkspace(false); setAutolabelOpen(true); }} /> : <>
            <Sidebar />
            <AnnotationCanvas />
            {autolabelOpen && <AutolabelingPanel onClose={() => setAutolabelOpen(false)} />}
          </>}
        </div>
        {running && <div role="status" style={{ padding: "4px 16px", background: "var(--color-panel)", fontSize: 12 }}>Autolabeling em andamento · você pode continuar anotando</div>}
        <Statusbar />
      </div>

      <ExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        totalFrames={totalFrames}
      />
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <ConfirmModal
        open={confirmStopOpen}
        title="Encerrar sessão de anotação?"
        description="As anotações são salvas automaticamente. Você poderá retomar este projeto mais tarde usando a opção 'Importar anotações existentes'."
        confirmLabel="Encerrar sessão"
        danger
        onConfirm={handleStopConfirm}
        onCancel={() => setConfirmStopOpen(false)}
      />
    </div>
  );
}
