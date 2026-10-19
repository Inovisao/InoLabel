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

/** Corpo do POST em lote para colar: copia classe, geometria e ID; sem id/score do original. */
export function pastePayload(clipboard: Annotation[], imgW: number, imgH: number) {
  const inside = clipboard.filter(({ bbox: [x, y, w, h] }) => x < imgW && y < imgH && x + w > 0 && y + h > 0);
  return {
    skipped: clipboard.length - inside.length,
    annotations: inside.map((ann) => ({
      category_id: ann.category_id,
      bbox: ann.bbox,
      source: "manual",
      ...(ann.obb ? { obb: ann.obb } : {}),
      ...(ann.keypoints ? { keypoints: ann.keypoints } : {}),
      ...(ann.track_id != null ? { track_id: ann.track_id } : {}),
    })),
  };
}
