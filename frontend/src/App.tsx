import { useEffect, useState } from "react";
import { useSessionStore } from "./stores/session";
import WizardPage from "./pages/WizardPage";
import AnnotatePage from "./pages/AnnotatePage";
import ProjectsPage from "./pages/ProjectsPage";
import HistoryPage from "./pages/HistoryPage";
import HelpPage from "./pages/HelpPage";
import ShortcutsPage from "./pages/ShortcutsPage";
import { ToastProvider } from "./ui/ToastContext";
import type { WizardState } from "./components/wizard/Wizard";
import type { ProjectEntry } from "./api/types";

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
  const [view, setView] = useState<AppView>("mode");
  const [wizardInitial, setWizardInitial] = useState<Partial<WizardState> | undefined>(undefined);

  // On mount: reconnect to any session still running on the server (e.g. after
  // a page refresh). recover() is a no-op when no server session exists.
  useEffect(() => {
    recover();
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
    <ToastProvider>
      {active ? (
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
  );
}
