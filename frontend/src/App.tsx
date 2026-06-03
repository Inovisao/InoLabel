import { useState } from "react";
import { useSessionStore } from "./stores/session";
import WizardPage from "./pages/WizardPage";
import AnnotatePage from "./pages/AnnotatePage";
import ProjectsPage from "./pages/ProjectsPage";
import HistoryPage from "./pages/HistoryPage";
import HelpPage from "./pages/HelpPage";
import ShortcutsPage from "./pages/ShortcutsPage";
import { ToastProvider } from "./ui/ToastContext";

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
  const [view, setView] = useState<AppView>("mode");

  const wizardStep = WIZARD_STEPS.indexOf(view);
  const isWizard = wizardStep !== -1;

  const handleNavigate = (id: string) => setView(id as AppView);

  return (
    <ToastProvider>
      {active ? (
        <AnnotatePage />
      ) : isWizard ? (
        <WizardPage
          step={wizardStep}
          onStepChange={(s) => setView(WIZARD_STEPS[s])}
          activeNav={view}
          onNavigate={handleNavigate}
        />
      ) : view === "projects" ? (
        <ProjectsPage activeNav={view} onNavigate={handleNavigate} />
      ) : view === "history" ? (
        <HistoryPage activeNav={view} onNavigate={handleNavigate} />
      ) : view === "help" ? (
        <HelpPage activeNav={view} onNavigate={handleNavigate} />
      ) : (
        <ShortcutsPage activeNav={view} onNavigate={handleNavigate} />
      )}
    </ToastProvider>
  );
}
