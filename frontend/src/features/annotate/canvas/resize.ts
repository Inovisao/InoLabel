/**
 * Redimensionar caixa pelas alças (Konva Transformer): limites e conversão para px da
 * imagem. Funções puras (testadas em frontend/tests).
 */

/** Caixa como o Transformer a entrega (px de tela). */
export interface ScreenBox {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
}

/** Área da imagem no canvas (px de tela). */
export interface Area {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Caixa proposta pela alça, recortada à imagem. Menor que `minSize` (ou invertida, ao
 * passar a alça do lado oposto) mantém a anterior: a caixa não some nem vira do avesso.
 */
export function boundResize(oldBox: ScreenBox, newBox: ScreenBox, area: Area, minSize: number): ScreenBox {
  const x1 = Math.max(newBox.x, area.x);
  const y1 = Math.max(newBox.y, area.y);
  const x2 = Math.min(newBox.x + newBox.width, area.x + area.w);
  const y2 = Math.min(newBox.y + newBox.height, area.y + area.h);
  if (newBox.width < minSize || newBox.height < minSize || x2 - x1 < minSize || y2 - y1 < minSize) return oldBox;
  return { ...newBox, x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
}

/** Caixa na tela → bbox [x, y, largura, altura] em px da imagem. */
export function bboxFromScreen(
  box: { x: number; y: number; width: number; height: number },
  fit: { offsetX: number; offsetY: number; scale: number }
): [number, number, number, number] {
  return [
    (box.x - fit.offsetX) / fit.scale,
    (box.y - fit.offsetY) / fit.scale,
    box.width / fit.scale,
    box.height / fit.scale,
  ];
}
