/** Regras puras da edição de classes no meio da anotação (testadas em frontend/tests). */

/**
 * Classe ativa depois de remover `removed`: as seguintes descem uma posição;
 * se a ativa foi a removida, volta para a primeira.
 */
export function selectedAfterRemoval(selected: number, removed: number): number {
  if (selected === removed) return 0;
  return selected > removed ? selected - 1 : selected;
}

/** Nomes de pontos digitados separados por vírgula (modo keypoint). */
export function parsePointNames(text: string): string[] {
  return text.split(",").map((name) => name.trim()).filter(Boolean);
}

/** Texto da confirmação de remoção, com o que será apagado no projeto. */
export function removalWarning(name: string, annotations: number, frames: number): string {
  if (!annotations) return `A classe "${name}" não tem anotações. As classes seguintes sobem uma posição na lista.`;
  const anns = annotations === 1 ? "1 anotação" : `${annotations} anotações`;
  const fr = frames === 1 ? "1 frame" : `${frames} frames`;
  return `Isso apaga ${anns} da classe "${name}" em ${fr} do projeto. As classes seguintes sobem uma posição na lista. Esta ação não pode ser desfeita.`;
}
