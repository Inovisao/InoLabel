import { useState } from "react";
import { Check, Info } from "lucide-react";
import { useSessionStore } from "../../stores/session";
import NavSidebar from "../layout/NavSidebar";
import WizardTopbar from "../layout/WizardTopbar";
import StepMode from "./StepMode";
import StepData from "./StepData";
import StepConfig from "./StepConfig";
import type { TaskMode } from "../../api/types";

export interface WizardState {
  mode: TaskMode;
  dataRoot: string;
  outputDir: string;
  classes: string[];
  weightsPath: string;
  confidence: number;
  resumeExisting: boolean;
}

const INITIAL: WizardState = {
  mode: "detection",
  dataRoot: "",
  outputDir: "output",
  classes: [],
  weightsPath: "",
  confidence: 0.4,
  resumeExisting: false,
};

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
  const [state, setState] = useState<WizardState>({ ...INITIAL, ...initialState });
  const { start, loading, error } = useSessionStore();

  const update = (patch: Partial<WizardState>) =>
    setState((s) => ({ ...s, ...patch }));

  const next = () => onStepChange(Math.min(step + 1, 2));
  const back = () => onStepChange(Math.max(step - 1, 0));

  const finish = async () => {
    await start({
      mode: state.mode,
      data_root: state.dataRoot,
      output_dir: state.outputDir,
      classes: state.classes,
      weights_paths: state.weightsPath ? [state.weightsPath] : [],
      confidence_threshold: state.confidence,
      resume_existing: state.resumeExisting,
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
          <HeroSection title={HERO[step].title} subtitle={HERO[step].subtitle} />

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

          {error && (
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                background: "rgba(220,38,38,0.06)",
                border: "1px solid rgba(220,38,38,0.25)",
                borderRadius: "var(--radius-md)",
                color: "var(--color-danger)",
                fontSize: 13,
              }}
            >
              {error}
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
                <button className="btn-primary" onClick={next}>
                  Continuar →
                </button>
              ) : (
                <button className="btn-primary" onClick={finish} disabled={loading}>
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

/* ── Hero ─────────────────────────────────────────── */

function HeroSection({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div
      style={{
        background: "var(--color-hero-bg)",
        borderRadius: "var(--radius-xl)",
        padding: "28px 32px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ maxWidth: 520, position: "relative", zIndex: 1 }}>
        <h1 className="text-display" style={{ marginBottom: 8 }}>{title}</h1>
        <p className="text-page-subtitle">{subtitle}</p>
      </div>
      <div
        style={{
          position: "absolute",
          right: 0,
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
          opacity: 0.85,
        }}
      >
        <HeroIllustration />
      </div>
    </div>
  );
}

/* ── Stepper ──────────────────────────────────────── */

function StepperBar({ current, labels }: { current: number; labels: string[] }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginTop: 24 }}>
      {labels.map((label, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            flex: i < labels.length - 1 ? 1 : undefined,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: i <= current ? "var(--color-primary)" : "var(--color-border)",
                color: i <= current ? "#fff" : "#9CA3AF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
                fontWeight: 700,
                flexShrink: 0,
                transition: "background 200ms",
              }}
            >
              {i < current ? <Check size={14} strokeWidth={3} /> : i + 1}
            </div>
            <span
              style={{
                fontSize: 13,
                fontWeight: i === current ? 600 : 400,
                color: i <= current ? "var(--color-primary)" : "#9CA3AF",
                transition: "color 200ms",
              }}
            >
              {label}
            </span>
          </div>
          {i < labels.length - 1 && <div className="stepper-connector" />}
        </div>
      ))}
    </div>
  );
}

/* ── Illustration ─────────────────────────────────── */

function HeroIllustration() {
  return (
    <svg width="240" height="190" viewBox="0 0 240 190" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="80,50 130,28 200,28 150,50" fill="rgba(165,180,252,0.12)" stroke="#A5B4FC" strokeWidth="1.5" strokeLinejoin="round" />
      <polygon points="150,50 200,28 200,110 150,132" fill="rgba(165,180,252,0.1)" stroke="#A5B4FC" strokeWidth="1.5" strokeLinejoin="round" />
      <polygon points="80,50 150,50 150,132 80,132" fill="rgba(165,180,252,0.08)" stroke="#A5B4FC" strokeWidth="1.5" strokeLinejoin="round" />
      {([
        [80, 50], [150, 50], [80, 132], [150, 132],
        [130, 28], [200, 28], [200, 110],
      ] as [number, number][]).map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="3.5" fill="#A5B4FC" />
      ))}
      <rect x="148" y="124" width="78" height="54" rx="10" fill="white" filter="drop-shadow(0 4px 12px rgba(99,102,241,0.18))" />
      <rect x="156" y="132" width="22" height="16" rx="4" fill="#EEF2FF" />
      <circle cx="159.5" cy="135.5" r="2.5" fill="#A5B4FC" />
      <path d="M156 147l5-5 4 4 3-3 6 6" stroke="#A5B4FC" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <rect x="182" y="133" width="36" height="3" rx="1.5" fill="#E5E7EB" />
      <rect x="182" y="140" width="26" height="3" rx="1.5" fill="#E5E7EB" />
      <rect x="186" y="38" width="46" height="26" rx="13" fill="#F3F4F6" />
      <text x="209" y="55" textAnchor="middle" fontSize="11" fill="#6B7280" fontFamily="monospace" fontWeight="600">{"</>"}</text>
      <circle cx="52" cy="48" r="2.5" fill="#C7D2FE" opacity="0.8" />
      <circle cx="44" cy="60" r="1.8" fill="#C7D2FE" opacity="0.5" />
      <circle cx="58" cy="70" r="1.5" fill="#C7D2FE" opacity="0.4" />
    </svg>
  );
}
