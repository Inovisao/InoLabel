/**
 * Etiquetas de classe que tapam a imagem: a etiqueta fica acima da caixa e, com caixas
 * empilhadas, cobre o conteúdo da caixa de cima. Com o ponteiro ali, ela fica transparente.
 * Funções puras, em px de tela (testadas em frontend/tests).
 */

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Tamanho da etiqueta proporcional à largura da forma (entre 10 e 14 px). */
export function labelFontSize(shapeWidth: number): number {
  return Math.max(10, Math.min(14, shapeWidth * 0.12));
}

/** Fundo da etiqueta ancorada em (x, y), o canto superior esquerdo da forma. */
export function labelRect(x: number, y: number, label: string, fontSize: number): Rect {
  return {
    x,
    y: Math.max(0, y - fontSize - 4),
    w: label.length * fontSize * 0.6 + 8,
    h: fontSize + 4,
  };
}

/** Menor retângulo com todos os pontos (contorno de uma OBB na tela). */
export function boundsOf(points: [number, number][]): Rect {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}

const contains = (r: Rect, x: number, y: number) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;

const intersects = (a: Rect, b: Rect) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/**
 * Etiquetas a deixar transparentes: as que estão sob o ponteiro e as que invadem a
 * forma sob o ponteiro (`hovered`). A etiqueta da própria forma, que fica fora dela,
 * só some se o ponteiro estiver em cima dela.
 */
export function fadedLabelIds(
  labels: { id: number; rect: Rect }[],
  pointer: { x: number; y: number } | null,
  hovered: { id: number; bounds: Rect } | null
): number[] {
  if (!pointer) return [];
  return labels
    .filter(({ id, rect }) =>
      contains(rect, pointer.x, pointer.y) || (hovered !== null && id !== hovered.id && intersects(rect, hovered.bounds))
    )
    .map(({ id }) => id)
    .sort((a, b) => a - b);
}
