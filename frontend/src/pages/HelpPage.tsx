import { ScanLine, BoxSelect, Diamond, Grid2X2, HelpCircle } from "lucide-react";
import PageShell from "../components/layout/PageShell";

interface Props {
  activeNav: string;
  onNavigate: (id: string) => void;
}

const MODES = [
  {
    icon: BoxSelect,
    label: "Detecção padrão",
    color: "#DBEAFE",
    iconColor: "#3B82F6",
    desc: "Cria bounding boxes independentes por frame. Cada frame é anotado de forma autônoma, sem rastrear objetos entre quadros. Ideal para datasets de detecção de objetos.",
  },
  {
    icon: ScanLine,
    label: "Rastreamento",
    color: "#DBEAFE",
    iconColor: "#3B82F6",
    desc: "Mantém a identidade de objetos entre frames usando o BYTETracker. Cada objeto recebe um track_id persistente. Ideal para datasets de tracking em vídeo.",
  },
  {
    icon: Diamond,
    label: "Detecção orientada (OBB)",
    color: "#DCFCE7",
    iconColor: "#22C55E",
    desc: "Caixas delimitadoras rotacionadas com ângulo. Útil para objetos aéreos (satélites, drones) onde a orientação importa. Exportado em formato YOLO OBB.",
  },
  {
    icon: Grid2X2,
    label: "Classificação",
    color: "#FEF3C7",
    iconColor: "#F59E0B",
    desc: "Organiza imagens inteiras em subpastas por classe com um keypress. Sem bounding boxes — útil para datasets de classificação de imagens.",
  },
];

const WORKFLOW = [
  { step: "1", title: "Configure o modo", desc: "Escolha o tipo de tarefa de anotação que melhor se aplica ao seu dataset." },
  { step: "2", title: "Aponte os dados", desc: "Informe a pasta com as imagens ou o arquivo de vídeo a ser anotado." },
  { step: "3", title: "Defina as classes", desc: "Crie as categorias de objetos que você vai anotar e ajuste a confiança do modelo." },
  { step: "4", title: "Anote os frames", desc: "Use o canvas para desenhar bboxes. Navegue com ← → ou A/D. As anotações são salvas automaticamente." },
];

export default function HelpPage({ activeNav, onNavigate }: Props) {
  return (
    <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Ajuda">
      {/* Hero */}
      <div
        style={{
          background: "var(--color-hero-bg)",
          borderRadius: "var(--radius-xl)",
          padding: "28px 32px",
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <HelpCircle size={28} color="var(--color-primary)" strokeWidth={1.75} />
          <h1 className="text-display">Ajuda</h1>
        </div>
        <p className="text-page-subtitle">Documentação dos modos de anotação e do fluxo de trabalho.</p>
      </div>

      {/* Workflow */}
      <Section title="Fluxo de trabalho">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {WORKFLOW.map((w) => (
            <div
              key={w.step}
              style={{
                display: "flex",
                gap: 14,
                padding: "16px 18px",
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: "var(--color-primary)",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 14,
                  fontWeight: 700,
                  flexShrink: 0,
                }}
              >
                {w.step}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-text)", marginBottom: 4 }}>
                  {w.title}
                </div>
                <div style={{ fontSize: 13, color: "var(--color-muted)", lineHeight: 1.5 }}>
                  {w.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Modes */}
      <Section title="Modos de anotação">
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {MODES.map((m) => {
            const Icon = m.icon;
            return (
              <div
                key={m.label}
                style={{
                  display: "flex",
                  gap: 16,
                  padding: "18px 20px",
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 10,
                    background: m.color,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <Icon size={22} color={m.iconColor} strokeWidth={1.75} />
                </div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: "var(--color-text)", marginBottom: 4 }}>
                    {m.label}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--color-muted)", lineHeight: 1.55 }}>
                    {m.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Section>
    </PageShell>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "var(--color-panel)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        padding: 24,
        marginBottom: 16,
      }}
    >
      <h2
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: "var(--color-text)",
          marginBottom: 16,
          paddingBottom: 12,
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        {title}
      </h2>
      {children}
    </div>
  );
}
