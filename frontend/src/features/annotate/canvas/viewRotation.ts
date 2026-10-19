/**
 * Girar a exibição em passos de 90° (como na 1.0): só visual. A camada do Konva gira em
 * torno do centro do canvas; dentro dela tudo continua no espaço "local", alinhado à
 * imagem original, e as coordenadas gravadas não mudam. Estas funções puras convertem
 * entre a tela (stage) e o espaço local (testadas em frontend/tests).
 */

export type Rotation = 0 | 90 | 180 | 270;

export interface Point {
  x: number;
  y: number;
}

/** Próximo passo de 90° (horário com +90, anti-horário com -90). */
export function rotateBy(r: Rotation, step: 90 | -90): Rotation {
  return ((((r + step) % 360) + 360) % 360) as Rotation;
}

/** Tamanho do espaço local: em 90°/270° a largura e a altura da tela trocam de papel. */
export function localSize(width: number, height: number, r: Rotation) {
  return r % 180 ? { width: height, height: width } : { width, height };
}

// Seno e cosseno exatos dos múltiplos de 90° (sem resíduo de ponto flutuante).
const COS: Record<Rotation, number> = { 0: 1, 90: 0, 180: -1, 270: 0 };
const SIN: Record<Rotation, number> = { 0: 0, 90: 1, 180: 0, 270: -1 };

/** Vetor girado `r` graus no sentido horário da tela (y para baixo). */
export function vectorToScreen(v: Point, r: Rotation): Point {
  return { x: v.x * COS[r] - v.y * SIN[r] || 0, y: v.x * SIN[r] + v.y * COS[r] || 0 };
}

/** Vetor da tela levado ao espaço local (ex.: Alt+→ move para a direita na tela). */
export function vectorToLocal(v: Point, r: Rotation): Point {
  return { x: v.x * COS[r] + v.y * SIN[r] || 0, y: -v.x * SIN[r] + v.y * COS[r] || 0 };
}

/** Atributos da camada Konva: gira o espaço local em torno do centro do canvas. */
export function layerTransform(width: number, height: number, r: Rotation) {
  const local = localSize(width, height, r);
  return { x: width / 2, y: height / 2, offsetX: local.width / 2, offsetY: local.height / 2, rotation: r };
}

export function localToScreen(p: Point, width: number, height: number, r: Rotation): Point {
  const local = localSize(width, height, r);
  const v = vectorToScreen({ x: p.x - local.width / 2, y: p.y - local.height / 2 }, r);
  return { x: width / 2 + v.x, y: height / 2 + v.y };
}

export function screenToLocal(p: Point, width: number, height: number, r: Rotation): Point {
  const local = localSize(width, height, r);
  const v = vectorToLocal({ x: p.x - width / 2, y: p.y - height / 2 }, r);
  return { x: local.width / 2 + v.x, y: local.height / 2 + v.y };
}

/**
 * Onde pôr a etiqueta de uma forma com a exibição girada: no canto superior esquerdo do
 * contorno *na tela* (para o texto ficar em pé), devolvido nos dois espaços.
 */
export function labelAnchor(localPoints: [number, number][], width: number, height: number, r: Rotation) {
  const screen = localPoints.map(([x, y]) => localToScreen({ x, y }, width, height, r));
  const top = { x: Math.min(...screen.map((p) => p.x)), y: Math.min(...screen.map((p) => p.y)) };
  return { screen: top, local: screenToLocal(top, width, height, r) };
}
