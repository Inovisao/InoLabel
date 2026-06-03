import Wizard from "../components/wizard/Wizard";

interface Props {
  step: number;
  onStepChange: (s: number) => void;
  activeNav: string;
  onNavigate: (id: string) => void;
}

export default function WizardPage({ step, onStepChange, activeNav, onNavigate }: Props) {
  return (
    <Wizard
      step={step}
      onStepChange={onStepChange}
      activeNav={activeNav}
      onNavigate={onNavigate}
    />
  );
}
