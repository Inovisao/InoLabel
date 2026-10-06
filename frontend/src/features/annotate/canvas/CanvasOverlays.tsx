import type { ClassItem, TaskMode } from "../../../shared/api/types";
import type { KeypointVisibility, KeypointWip, Tool } from "../store";

const pill = {
  position: "absolute" as const,
  background: "var(--overlay-canvas-control)",
  color: "var(--color-text-inverse)",
  pointerEvents: "none" as const,
};

/** Erro da última operação; clique para fechar. */
export function ErrorToast({ error, onClose }: { error: string; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "absolute",
        top: 12,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 10,
        padding: "8px 16px",
        background: "var(--overlay-canvas-error)",
        color: "var(--color-text-inverse)",
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 500,
        cursor: "pointer",
        backdropFilter: "blur(4px)",
        maxWidth: 400,
        textAlign: "center",
      }}
    >
      {error} · clique para fechar
    </div>
  );
}

export function LoadingFrame() {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--color-canvas-muted)",
        fontSize: 14,
        gap: 8,
        pointerEvents: "none",
      }}
    >
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.4">
        <rect x="8" y="8" width="32" height="32" rx="4" stroke="var(--color-text-inverse)" strokeWidth="1.5" />
        <circle cx="18" cy="20" r="3" stroke="var(--color-text-inverse)" strokeWidth="1.5" />
        <path d="M8 34l9-9 5 5 7-8 11 12" stroke="var(--color-text-inverse)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>Carregando frame…</span>
    </div>
  );
}

/** Classe ativa (canto inferior direito). */
export function ActiveClassBadge({ cls }: { cls: ClassItem }) {
  return (
    <div
      style={{
        ...pill,
        bottom: 12,
        right: 12,
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 10px",
        backdropFilter: "blur(4px)",
        borderRadius: 999,
      }}
    >
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: cls.color ?? "#4F46E5", flexShrink: 0 }} />
      <span style={{ fontSize: 12, color: "var(--color-text-inverse)", fontWeight: 500 }}>{cls.name}</span>
    </div>
  );
}

/** Keypoint: qual é o próximo ponto da instância e com que visibilidade ele entra. */
export function NextKeypointBanner({
  cls,
  wip,
  visibility,
}: {
  cls: ClassItem | undefined;
  wip: KeypointWip | null;
  visibility: KeypointVisibility;
}) {
  const names = cls?.keypoints ?? [];
  if (!names.length) return null;
  const index = wip?.index ?? 0;
  return (
    <div
      style={{
        ...pill,
        top: 12,
        left: "50%",
        transform: "translateX(-50%)",
        padding: "6px 12px",
        borderRadius: "var(--radius-md)",
        fontSize: 12,
        whiteSpace: "nowrap",
      }}
    >
      {cls?.name} · próximo: <strong>{names[index]}</strong> ({index + 1}/{names.length})
      {" · "}
      {visibility === 2 ? "visível" : "oculto"}
    </div>
  );
}

/** Classe já atribuída à imagem (modo classificação). */
export function ClassificationBadge({ name }: { name: string | undefined }) {
  return (
    <div
      style={{
        ...pill,
        top: 12,
        right: 12,
        padding: "8px 12px",
        borderRadius: "var(--radius-md)",
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      Classe: {name}
    </div>
  );
}

/** Dica de uso no canto inferior esquerdo, conforme modo e ferramenta. */
export function CanvasHint({ mode, tool, hasSelection }: { mode: TaskMode | null; tool: Tool; hasSelection: boolean }) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 12,
        left: 12,
        fontSize: 11,
        color: "var(--color-canvas-subtle)",
        pointerEvents: "none",
      }}
    >
      {hintText(mode, tool, hasSelection)}
    </div>
  );
}

function hintText(mode: TaskMode | null, tool: Tool, hasSelection: boolean): string {
  if (mode === "classification") return "Clique na classe ou digite o número dela · Espaço pula · Ctrl+Z desfaz";
  if (mode === "keypoint") {
    return tool === "select"
      ? "Clique num ponto para selecionar · arraste para mover · C visível/oculto · Del apaga a instância · B volta a marcar"
      : "Clique para marcar os pontos em ordem · X pula o ponto · C visível/oculto · F fecha · Backspace desfaz o ponto · Esc cancela";
  }
  if (mode === "obb" && hasSelection) {
    return "Arraste a alça ○ para girar (Shift: 15°) · Q / E giram 5° · V e arraste para mover · Del remove";
  }
  return tool === "select"
    ? "Clique para selecionar · arraste a caixa selecionada para mover · Del remove · B volta a desenhar"
    : "Arraste para anotar · clique numa caixa para editar · N marca frame sem objetos · Ctrl+Z desfaz";
}
