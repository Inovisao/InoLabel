/** Nomes dos modos de anotação exibidos na interface. */

/** Barra superior e rodapé da anotação. */
export const MODE_LABELS: Record<string, string> = {
  tracking: "Rastreamento",
  detection: "Detecção",
  obb: "OBB",
  keypoint: "Keypoints",
  classification: "Classificação",
};

/** Configurações da sessão (nome completo do modo). */
export const MODE_LABELS_LONG: Record<string, string> = {
  ...MODE_LABELS,
  detection: "Detecção padrão",
  obb: "Detecção orientada (OBB)",
};

/** Cartões de projeto (Projetos e Histórico); "unknown" = projeto antigo sem modo. */
export const PROJECT_MODE_LABELS: Record<string, string> = {
  ...MODE_LABELS,
  tracking: "Tracking",
  unknown: "—",
};
