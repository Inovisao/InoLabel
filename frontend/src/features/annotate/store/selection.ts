/**
 * Seleção de várias anotações, copiar/colar e mover o bloco: regras puras, em px da
 * imagem (testadas em frontend/tests). Só `import type`, para rodar no node --test.
 */
import type { Annotation, AnnotationPatch } from "../../../shared/api/types";

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

/** Bloco copiado, com o tamanho da imagem de onde saiu. */
export interface Clipboard {
  annotations: Annotation[];
  width: number;
  height: number;
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

/**
 * Anotação levada para uma imagem de outro tamanho, na mesma posição relativa (um campo
 * a 30% da largura continua a 30%). A OBB girada com escalas diferentes em x e y é
 * aproximada: o ângulo fica e cada lado escala pela sua direção.
 */
export function scaleAnnotation(ann: Annotation, sx: number, sy: number): Annotation {
  if (sx === 1 && sy === 1) return ann;
  const [x, y, w, h] = ann.bbox;
  const scaled: Annotation = { ...ann, bbox: [x * sx, y * sy, w * sx, h * sy] };
  if (ann.obb) {
    const t = (ann.obb.angle * Math.PI) / 180;
    scaled.obb = {
      ...ann.obb,
      cx: ann.obb.cx * sx,
      cy: ann.obb.cy * sy,
      width: ann.obb.width * Math.hypot(sx * Math.cos(t), sy * Math.sin(t)),
      height: ann.obb.height * Math.hypot(sx * Math.sin(t), sy * Math.cos(t)),
    };
  }
  if (ann.keypoints) scaled.keypoints = ann.keypoints.map(([px, py, v]) => [px * sx, py * sy, v]);
  return scaled;
}

/**
 * Corpo do POST em lote para colar numa imagem de `imgW`×`imgH`: escala o bloco se a
 * imagem de origem tinha outro tamanho e descarta o que ficar fora da imagem.
 */
export function pastePayload(clipboard: Clipboard, imgW: number, imgH: number) {
  const sx = clipboard.width ? imgW / clipboard.width : 1;
  const sy = clipboard.height ? imgH / clipboard.height : 1;
  const scaled = clipboard.annotations.map((ann) => scaleAnnotation(ann, sx, sy));
  const inside = scaled.filter(({ bbox: [x, y, w, h] }) => x < imgW && y < imgH && x + w > 0 && y + h > 0);
  return {
    skipped: scaled.length - inside.length,
    annotations: inside.map(createPayload),
  };
}
