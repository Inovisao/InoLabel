/**
 * Seleção de várias anotações, copiar/colar e mover o bloco: regras puras, em px da
 * imagem (testadas em frontend/tests). Só `import type`, para rodar no node --test.
 */
import type { Annotation, AnnotationPatch } from "../../../shared/api/types";
import type { Rotation } from "../canvas/viewRotation";

export interface ImageRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Liga/desliga uma anotação na seleção (Shift+clique). */
export function toggleId(ids: number[], id: number): number[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}

/** Retângulo de arrastar a partir de dois cantos quaisquer. */
export function rectFromCorners(a: { x: number; y: number }, b: { x: number; y: number }): ImageRect {
  return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) };
}

/**
 * Anotações do retângulo de seleção: as que têm o centro dentro dele. Com caixas
 * coladas umas nas outras (formulários), pegar só o que encosta selecionaria vizinhas.
 */
export function idsInRect(annotations: Annotation[], rect: ImageRect): number[] {
  return annotations
    .filter(({ bbox: [x, y, w, h] }) => {
      const cx = x + w / 2;
      const cy = y + h / 2;
      return cx >= rect.x && cx <= rect.x + rect.w && cy >= rect.y && cy <= rect.y + rect.h;
    })
    .map((a) => a.id);
}

/**
 * Deslocamento de uma caixa do bloco, preso à imagem só para ela: a caixa encostada na
 * borda fica parada contra ela e as outras seguem. (Prender o bloco inteiro pela caixa
 * mais perto da borda travava tudo quando uma caixa encostava na borda.) Caixa que já
 * passa da borda não é empurrada para dentro, só não sai mais.
 */
export function boxDelta(bbox: number[], dx: number, dy: number, imgW: number, imgH: number) {
  const [x, y, w, h] = bbox;
  const axis = (d: number, start: number, size: number, limit: number) =>
    // `|| 0`: sem isso uma caixa na borda zero devolve -0.
    Math.max(Math.min(0, -start), Math.min(d, Math.max(0, limit - start - size))) || 0;
  return { dx: axis(dx, x, w, imgW), dy: axis(dy, y, h, imgH) };
}

/** PATCH que desloca a anotação: caixa e OBB pela bbox (o backend translada o OBB); keypoint pelos pontos. */
export function movedPatch(ann: Annotation, dx: number, dy: number): AnnotationPatch {
  if (ann.keypoints) {
    return { keypoints: ann.keypoints.map(([x, y, v]) => (v > 0 ? [x + dx, y + dy, v] : [x, y, v])) };
  }
  const [x, y, w, h] = ann.bbox;
  return { bbox: [x + dx, y + dy, w, h] };
}

/** Valores de antes do movimento, para o Ctrl+Z (mesmo formato do PATCH). */
export function beforeMovePatch(ann: Annotation): AnnotationPatch {
  if (ann.keypoints) return { keypoints: ann.keypoints };
  if (ann.obb) return { obb: ann.obb };
  return { bbox: ann.bbox };
}

/** Bloco copiado, com o tamanho da imagem de onde saiu e a rotação da exibição na cópia. */
export interface Clipboard {
  annotations: Annotation[];
  width: number;
  height: number;
  rotation: Rotation;
}

/** Imagem e rotação da exibição de um lado da cópia (origem ou destino). */
export interface PasteSpace {
  width: number;
  height: number;
  rotation: Rotation;
}

/** Corpo do POST para recriar a anotação: classe, geometria e ID; sem id/score do original. */
export function createPayload(ann: Annotation) {
  return {
    category_id: ann.category_id,
    bbox: ann.bbox,
    source: "manual",
    ...(ann.obb ? { obb: ann.obb } : {}),
    ...(ann.keypoints ? { keypoints: ann.keypoints } : {}),
    ...(ann.track_id != null ? { track_id: ann.track_id } : {}),
  };
}

// Ponto normalizado da imagem (0..1) → posição na tela girada `r` (horário), e o inverso.
const TO_VIEW: Record<Rotation, (a: number, b: number) => [number, number]> = {
  0: (a, b) => [a, b],
  90: (a, b) => [1 - b, a],
  180: (a, b) => [1 - a, 1 - b],
  270: (a, b) => [b, 1 - a],
};
const FROM_VIEW: Record<Rotation, (u: number, v: number) => [number, number]> = {
  0: (u, v) => [u, v],
  90: (u, v) => [v, 1 - u],
  180: (u, v) => [1 - u, 1 - v],
  270: (u, v) => [1 - v, u],
};

/** Cantos da OBB em px da imagem (mesma ordem de obbGeometry.obbCorners). */
function obbCorners({ cx, cy, width, height, angle }: NonNullable<Annotation["obb"]>): [number, number][] {
  const t = (angle * Math.PI) / 180;
  const [c, s] = [Math.cos(t), Math.sin(t)];
  return ([[-1, -1], [1, -1], [1, 1], [-1, 1]] as const).map(([kx, ky]) => {
    const [dx, dy] = [(kx * width) / 2, (ky * height) / 2];
    return [cx + dx * c - dy * s, cy + dx * s + dy * c];
  });
}

/**
 * Anotação levada da imagem de origem para a de destino como ela aparecia na tela: a
 * mesma posição relativa (um campo a 30% da largura continua a 30%) e a mesma orientação
 * na tela, mesmo que cada imagem esteja com a exibição girada de um jeito (ex.: documento
 * deitado no arquivo, lido com a exibição girada 90°). Caixa continua alinhada aos eixos;
 * OBB é refeita pelos 4 cantos (aproximada se as escalas em x e y diferem).
 */
export function transformAnnotation(ann: Annotation, from: PasteSpace, to: PasteSpace): Annotation {
  if (from.rotation === to.rotation && from.width === to.width && from.height === to.height) return ann;
  const point = (x: number, y: number): [number, number] => {
    const [u, v] = TO_VIEW[from.rotation](x / from.width, y / from.height);
    const [a, b] = FROM_VIEW[to.rotation](u, v);
    return [a * to.width, b * to.height];
  };
  const [x, y, w, h] = ann.bbox;
  const [p, q] = [point(x, y), point(x + w, y + h)];
  const moved: Annotation = {
    ...ann,
    bbox: [Math.min(p[0], q[0]), Math.min(p[1], q[1]), Math.abs(q[0] - p[0]), Math.abs(q[1] - p[1])],
  };
  if (ann.obb) {
    const [c0, c1, c2, c3] = obbCorners(ann.obb).map(([cx, cy]) => point(cx, cy));
    moved.obb = {
      ...ann.obb,
      cx: (c0[0] + c1[0] + c2[0] + c3[0]) / 4,
      cy: (c0[1] + c1[1] + c2[1] + c3[1]) / 4,
      width: Math.hypot(c1[0] - c0[0], c1[1] - c0[1]),
      height: Math.hypot(c2[0] - c1[0], c2[1] - c1[1]),
      angle: (Math.atan2(c1[1] - c0[1], c1[0] - c0[0]) * 180) / Math.PI,
    };
  }
  if (ann.keypoints) moved.keypoints = ann.keypoints.map(([px, py, v]) => [...point(px, py), v]);
  return moved;
}

/**
 * Corpo do POST em lote para colar no destino: leva o bloco como ele aparecia na tela na
 * cópia (tamanho e rotação da exibição) e descarta o que ficar fora da imagem.
 */
export function pastePayload(clipboard: Clipboard, to: PasteSpace) {
  const from: PasteSpace = clipboard.width && clipboard.height ? clipboard : { ...to, rotation: clipboard.rotation };
  const scaled = clipboard.annotations.map((ann) => transformAnnotation(ann, from, to));
  const [imgW, imgH] = [to.width, to.height];
  const inside = scaled.filter(({ bbox: [x, y, w, h] }) => x < imgW && y < imgH && x + w > 0 && y + h > 0);
  return {
    skipped: scaled.length - inside.length,
    annotations: inside.map(createPayload),
  };
}
