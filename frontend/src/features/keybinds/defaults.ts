export const DEFAULT_BINDS = {
  next_frame: ["ArrowRight", "D"], prev_frame: ["ArrowLeft", "A"],
  tool_box: ["B"], tool_select: ["V"], mark_negative: ["N"],
  delete_annotation: ["Delete", "Backspace"], deselect: ["Escape"],
  rotate_left: ["Q"], rotate_right: ["E"],
  kp_skip: ["X"], kp_visibility: ["C"], kp_finish: ["F"],
  kp_undo: ["Backspace"], kp_cancel: ["Escape"],
  classification_skip: ["Space"], search_class: ["Slash"],
  save: ["Ctrl+S"], export: ["Ctrl+E"], settings: ["Ctrl+Comma"], undo: ["Ctrl+Z"],
} as const;

export type Action = keyof typeof DEFAULT_BINDS;
export type Binds = Record<Action, string[]>;
export interface Profiles { active_profile: string; profiles: Record<string, Binds> }

export const freshDefaults = (): Binds =>
  Object.fromEntries(Object.entries(DEFAULT_BINDS).map(([key, values]) => [key, [...values]])) as Binds;

export function restoreDefaults(current: Binds, defaults: Binds): Binds {
  return Object.fromEntries(
    (Object.keys(defaults) as Action[]).map((action) => [
      action,
      defaults[action].slice(0, Math.min(current[action].length, defaults[action].length)),
    ])
  ) as Binds;
}

export const DEFAULT_PROFILES = (): Profiles => ({ active_profile: "Padrão", profiles: { "Padrão": freshDefaults() } });

export const GROUPS: { title: string; actions: { id: Action; label: string }[] }[] = [
  { title: "Navegação", actions: [
    { id: "next_frame", label: "Próximo frame" }, { id: "prev_frame", label: "Frame anterior" },
  ] },
  { title: "Anotação", actions: [
    { id: "tool_box", label: "Caixa / marcar pontos" }, { id: "tool_select", label: "Selecionar" },
    { id: "mark_negative", label: "Frame sem objetos" }, { id: "delete_annotation", label: "Remover anotação" },
    { id: "deselect", label: "Desmarcar seleção" }, { id: "rotate_left", label: "Girar OBB à esquerda" },
    { id: "rotate_right", label: "Girar OBB à direita" },
  ] },
  { title: "Keypoints", actions: [
    { id: "kp_skip", label: "Pular ponto" }, { id: "kp_visibility", label: "Alternar visibilidade" },
    { id: "kp_finish", label: "Finalizar instância" }, { id: "kp_undo", label: "Desfazer ponto" },
    { id: "kp_cancel", label: "Cancelar instância" },
  ] },
  { title: "Classificação", actions: [{ id: "classification_skip", label: "Pular frame" }] },
  { title: "Sessão", actions: [
    { id: "search_class", label: "Buscar classe" }, { id: "save", label: "Salvar frame" },
    { id: "export", label: "Exportar" }, { id: "settings", label: "Configurações" },
    { id: "undo", label: "Desfazer" },
  ] },
];
