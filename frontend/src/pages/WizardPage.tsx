import Wizard from "../components/wizard/Wizard";
import type { WizardState } from "../components/wizard/Wizard";

interface Props {
  step: number;
  onStepChange: (s: number) => void;
  activeNav: string;
  onNavigate: (id: string) => void;
  initialState?: Partial<WizardState>;
}

export default function WizardPage({ step, onStepChange, activeNav, onNavigate, initialState }: Props) {
  return (
    <Wizard
      step={step}
      onStepChange={onStepChange}
      activeNav={activeNav}
      onNavigate={onNavigate}
      initialState={initialState}
    />
  );
}
