import { useState } from "react";
import { Info } from "lucide-react";
import { useSessionStore } from "../../shared/session/store";
import { useWorkspaceStore } from "../workspace/store";
import NavSidebar from "../../shared/layout/NavSidebar";
import WizardTopbar from "./WizardTopbar";
import StepMode from "./StepMode";
import StepData from "./StepData";
import StepConfig from "./StepConfig";
import StepperBar from "./StepperBar";
import WizardHero from "./WizardHero";
import { INITIAL_WIZARD_STATE, parseKeypointNames, type WizardState } from "./wizardState";

const STEP_LABELS = ["Modo", "Dados", "Configuração"];

const HERO = [
  { title: "Modo de anotação", subtitle: "Escolha o tipo de tarefa que deseja realizar." },
  { title: "Dados de entrada", subtitle: "Selecione a pasta com imagens ou vídeos para anotar." },
  { title: "Classes e configurações", subtitle: "Defina as classes de objetos e ajuste os parâmetros." },
];

interface Props {
  step: number;
  onStepChange: (s: number) => void;
  activeNav: string;
  onNavigate: (id: string) => void;
  initialState?: Partial<WizardState>;
}

export default function Wizard({ step, onStepChange, activeNav, onNavigate, initialState }: Props) {
  const [state, setState] = useState<WizardState>({ ...INITIAL_WIZARD_STATE, ...initialState });
  const { start, loading, error } = useSessionStore();
  const createProject = useWorkspaceStore((s) => s.createProject);
  const workspaceError = useWorkspaceStore((s) => s.error);

  const update = (patch: Partial<WizardState>) =>
    setState((s) => ({ ...s, ...patch }));

  const next = () => onStepChange(Math.min(step + 1, 2));

  // Projeto novo no modo keypoint: toda classe precisa dos seus pontos.
  const missingKeypoints =
    state.mode === "keypoint" &&
    !state.outputDir &&
    state.classes.some((name) => parseKeypointNames(state.keypointNames[name]).length === 0);
  const back = () => onStepChange(Math.max(step - 1, 0));

  const finish = async () => {
    // Projeto novo: a pasta é criada dentro do workspace (nunca um caminho relativo).
    const outputDir =
      state.outputDir ||
      (await createProject({
        name: state.projectName,
        mode: state.mode,
        data_path: state.dataRoot,
        classes: state.classes,
      }));
    if (!outputDir) return;
    update({ outputDir });
    await start({
      mode: state.mode,
      data_root: state.dataRoot,
      output_dir: outputDir,
      classes: state.classes,
      weights_paths: state.weightsPath ? [state.weightsPath] : [],
      confidence_threshold: state.confidence,
      resume_existing: state.resumeExisting,
      // Classe sem pontos digitados ao retomar: o backend usa os do próprio projeto.
      keypoint_classes:
        state.mode === "keypoint"
          ? state.classes
              .map((name) => ({ name, keypoints: parseKeypointNames(state.keypointNames[name]) }))
              .filter((spec) => spec.keypoints.length > 0)
          : undefined,
    });
  };

  const steps = [
    <StepMode key="mode" value={state.mode} onChange={(m) => update({ mode: m })} />,
    <StepData key="data" state={state} onChange={update} />,
    <StepConfig key="cfg" state={state} onChange={update} />,
  ];

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      <NavSidebar activeItem={activeNav} onNavigate={onNavigate} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <WizardTopbar />

        <main style={{ flex: 1, overflow: "auto", padding: "32px", background: "var(--color-bg)" }}>
          <WizardHero title={HERO[step].title} subtitle={HERO[step].subtitle} />

          {step > 0 && <StepperBar current={step} labels={STEP_LABELS} />}

          <div
            style={{
              background: "var(--color-panel)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-lg)",
              padding: 24,
              marginTop: 24,
            }}
          >
            {steps[step]}
          </div>

          {(error || workspaceError) && (
            <div
              className="alert alert-error"
              style={{
                marginTop: 12,
                fontSize: 13,
                color: "var(--alert-title)",
              }}
            >
              {error || workspaceError}
            </div>
          )}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginTop: 24,
              gap: 12,
            }}
          >
            {step === 0 ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  color: "var(--color-muted)",
                  fontSize: 13,
                  maxWidth: 480,
                }}
              >
                <Info size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                <span>
                  Você poderá alterar o modo de anotação a qualquer momento
                  nas configurações do projeto.
                </span>
              </div>
            ) : (
              <div />
            )}

            <div style={{ display: "flex", gap: 10, flexShrink: 0 }}>
              {step > 0 && (
                <button className="btn-secondary" onClick={back} disabled={loading}>
                  Voltar
                </button>
              )}
              {step < 2 ? (
                <button
                  className="btn-primary"
                  onClick={next}
                  disabled={step === 1 && (!state.dataRoot || (!state.outputDir && !state.projectName.trim()))}
                >
                  Continuar →
                </button>
              ) : (
                <button
                  className="btn-primary"
                  onClick={finish}
                  disabled={loading || missingKeypoints}
                  title={missingKeypoints ? "Defina os pontos de todas as classes" : undefined}
                >
                  {loading ? "Iniciando…" : "Iniciar anotação →"}
                </button>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

