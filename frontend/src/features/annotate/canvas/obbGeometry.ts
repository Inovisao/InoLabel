import type { OBBGeometry } from "../../../shared/api/types";

/** Geometria de caixas orientadas (OBB), em pixels da imagem. Mesma convenção do backend:
 * cantos na ordem (-w/2,-h/2), (w/2,-h/2), (w/2,h/2), (-w/2,h/2) girados por `angle` graus
 * (sentido horário na tela, pois o eixo y cresce para baixo). */

export type Point = [number, number];

export function obbCorners(obb: OBBGeometry): Point[] {
  const theta = (obb.angle * Math.PI) / 180;
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);
  const hw = obb.width / 2;
  const hh = obb.height / 2;
  return ([[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]] as Point[]).map(([dx, dy]) => [
    obb.cx + dx * cos - dy * sin,
    obb.cy + dx * sin + dy * cos,
  ]);
}

/** Ângulo em graus no intervalo (-180, 180]. */
export function normalizeAngle(angle: number): number {
  let value = angle % 360;
  if (value <= -180) value += 360;
  else if (value > 180) value -= 360;
  return value;
}

/** Ângulo (graus) do vetor centro → ponto. */
export function angleFromCenter(cx: number, cy: number, x: number, y: number): number {
  return (Math.atan2(y - cy, x - cx) * 180) / Math.PI;
}

export function pointInPolygon(x: number, y: number, polygon: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

/** Mesma caixa com `angle` normalizado e `points` recalculados. */
export function withCorners(obb: OBBGeometry): OBBGeometry {
  const next = { ...obb, angle: normalizeAngle(obb.angle), angle_unit: "degrees" as const };
  return { ...next, points: obbCorners(next) };
}

/**
 * Encaixa a caixa dentro da imagem deslocando o centro (ângulo e tamanho intactos).
 * Devolve null quando, nesse ângulo, ela não cabe de jeito nenhum — a edição é recusada.
 * Garante que nenhum canto saia da imagem, para o export não precisar cortar cantos.
 */
export function fitInsideImage(obb: OBBGeometry, imgW: number, imgH: number): OBBGeometry | null {
  const corners = obbCorners({ ...obb, cx: 0, cy: 0 });
  const halfX = Math.max(...corners.map(([x]) => Math.abs(x)));
  const halfY = Math.max(...corners.map(([, y]) => Math.abs(y)));
  if (halfX * 2 > imgW + 0.5 || halfY * 2 > imgH + 0.5) return null;
  const cx = Math.min(Math.max(obb.cx, halfX), imgW - halfX);
  const cy = Math.min(Math.max(obb.cy, halfY), imgH - halfY);
  return withCorners({ ...obb, cx, cy });
}

/** Gira a caixa para `angle` e a encaixa na imagem (null se não couber). */
export function rotateTo(obb: OBBGeometry, angle: number, imgW: number, imgH: number): OBBGeometry | null {
  return fitInsideImage({ ...obb, angle }, imgW, imgH);
}
