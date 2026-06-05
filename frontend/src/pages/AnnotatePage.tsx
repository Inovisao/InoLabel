import { useEffect, useState } from "react";
import NavSidebar from "../components/layout/NavSidebar";
import Topbar from "../components/layout/Topbar";
import Sidebar from "../components/layout/Sidebar";
import Statusbar from "../components/layout/Statusbar";
import AnnotationCanvas from "../components/canvas/AnnotationCanvas";
import ExportModal from "../components/modals/ExportModal";
import SettingsModal from "../components/modals/SettingsModal";
import ConfirmModal from "../components/modals/ConfirmModal";
import { useAnnotationStore } from "../stores/annotation";
import { useSessionStore } from "../stores/session";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { useToast } from "../ui/ToastContext";

interface Props {
  onStop?: (dest?: string) => void;
}

export default function AnnotatePage({ onStop }: Props) {
  const { fetchFrame, fetchClasses } = useAnnotationStore();
  const totalFrames = useSessionStore((s) => s.totalFrames);
  const { stop } = useSessionStore();
  const { toast } = useToast();

  const [exportOpen, setExportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [confirmStopOpen, setConfirmStopOpen] = useState(false);
  const [pendingNav, setPendingNav] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchClasses();
    fetchFrame();
  }, [fetchClasses, fetchFrame]);

  useKeyboardShortcuts({
    onExport: () => setExportOpen(true),
    onSettings: () => setSettingsOpen(true),
    onSave: () => toast("Anotações salvas automaticamente a cada operação.", "success"),
  });

  const handleNavRequest = (id: string) => {
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
      <NavSidebar activeItem="mode" onNavigate={handleNavRequest} />

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
          onExport={() => setExportOpen(true)}
          onSettings={() => setSettingsOpen(true)}
          onStop={handleTopbarStop}
        />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <Sidebar />
          <AnnotationCanvas />
        </div>
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
