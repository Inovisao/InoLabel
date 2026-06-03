import { useEffect, useState } from "react";
import NavSidebar from "../components/layout/NavSidebar";
import Topbar from "../components/layout/Topbar";
import Sidebar from "../components/layout/Sidebar";
import Statusbar from "../components/layout/Statusbar";
import AnnotationCanvas from "../components/canvas/AnnotationCanvas";
import ExportModal from "../components/modals/ExportModal";
import SettingsModal from "../components/modals/SettingsModal";
import { useAnnotationStore } from "../stores/annotation";
import { useSessionStore } from "../stores/session";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { useToast } from "../ui/ToastContext";

export default function AnnotatePage() {
  const { fetchFrame, fetchClasses } = useAnnotationStore();
  const totalFrames = useSessionStore((s) => s.totalFrames);
  const { toast } = useToast();

  const [exportOpen, setExportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    fetchClasses();
    fetchFrame();
  }, [fetchClasses, fetchFrame]);

  useKeyboardShortcuts({
    onExport: () => setExportOpen(true),
    onSettings: () => setSettingsOpen(true),
    onSave: () => toast("Anotações salvas automaticamente a cada operação.", "success"),
  });

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <NavSidebar activeItem="mode" />

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
    </div>
  );
}
