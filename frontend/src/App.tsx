import { useEffect, useState } from "react";
import { useSessionStore } from "./shared/session/store";
import { useWorkspaceStore } from "./features/workspace/store";
import WorkspaceGate from "./features/workspace/WorkspaceGate";
import WizardPage from "./features/wizard/WizardPage";
import AnnotatePage from "./features/annotate/AnnotatePage";
import ProjectsPage from "./features/projects/ProjectsPage";
import HistoryPage from "./features/projects/HistoryPage";
import HelpPage from "./features/help/HelpPage";
import ShortcutsPage from "./features/help/ShortcutsPage";
import { ToastProvider } from "./shared/ui/ToastContext";
import { ThemeProvider } from "./shared/ui/ThemeContext";
import type { WizardState } from "./features/wizard/wizardState";
import type { ProjectEntry } from "./shared/api/types";
import { useKeybindStore } from "./features/keybinds/store";

export type AppView =
  | "mode"
  | "data"
  | "config"
  | "projects"
  | "history"
  | "help"
  | "shortcuts";

const WIZARD_STEPS: AppView[] = ["mode", "data", "config"];

export default function App() {
  const active = useSessionStore((s) => s.active);
  const recover = useSessionStore((s) => s.recover);
  const workspace = useWorkspaceStore((s) => s.current);
  const workspaceLoaded = useWorkspaceStore((s) => s.loaded);
  const loadWorkspace = useWorkspaceStore((s) => s.load);
  const loadKeybinds = useKeybindStore((s) => s.load);
  const [view, setView] = useState<AppView>("mode");
  const [wizardInitial, setWizardInitial] = useState<Partial<WizardState> | undefined>(undefined);

  // On mount: reconnect to any session still running on the server (e.g. after
  // a page refresh). recover() is a no-op when no server session exists.
  useEffect(() => {
    recover();
    loadWorkspace();
    loadKeybinds();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const wizardStep = WIZARD_STEPS.indexOf(view);
  const isWizard = wizardStep !== -1;

  const handleNavigate = (id: string) => setView(id as AppView);

  // Called from ProjectsPage when user clicks "Continuar" on a project card.
  const handleResume = (project: ProjectEntry) => {
    setWizardInitial({
      mode: project.mode as WizardState["mode"],
      dataRoot: project.data_path,
      outputDir: project.path,
      classes: project.classes,
      resumeExisting: true,
    });
    setView("data"); // jump straight to step 1 (Dados), mode already selected
  };

  return (
    <ThemeProvider>
      <ToastProvider>
        {!active && workspaceLoaded && !workspace ? (
          <WorkspaceGate />
        ) : active ? (
          <AnnotatePage
            onStop={(dest) => {
              setWizardInitial(undefined);
              setView((dest || "mode") as AppView);
            }}
          />
        ) : isWizard ? (
          <WizardPage
            step={wizardStep}
            onStepChange={(s) => setView(WIZARD_STEPS[s])}
            activeNav={view}
            onNavigate={handleNavigate}
            initialState={wizardInitial}
          />
        ) : view === "projects" ? (
          <ProjectsPage activeNav={view} onNavigate={handleNavigate} onResume={handleResume} />
        ) : view === "history" ? (
          <HistoryPage activeNav={view} onNavigate={handleNavigate} onResume={handleResume} />
        ) : view === "help" ? (
          <HelpPage activeNav={view} onNavigate={handleNavigate} />
        ) : (
          <ShortcutsPage activeNav={view} onNavigate={handleNavigate} />
        )}
      </ToastProvider>
    </ThemeProvider>
  );
}
