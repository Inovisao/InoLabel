// Seleção em bloco, copiar/colar e mover. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Annotation } from "../src/shared/api/types.ts";
import {
  beforeMovePatch, boxDelta, idsInRect, movedPatch, pastePayload, rectFromCorners, toggleId, transformAnnotation,
} from "../src/features/annotate/store/selection.ts";

const box = (id: number, bbox: [number, number, number, number], extra: Partial<Annotation> = {}): Annotation =>
  ({ id, image_id: 0, category_id: 0, bbox, source: "manual", ...extra }) as Annotation;

test("Shift+clique liga e desliga da seleção", () => {
  assert.deepEqual(toggleId([1, 2], 3), [1, 2, 3]);
  assert.deepEqual(toggleId([1, 2, 3], 2), [1, 3]);
});

test("retângulo de seleção pega quem tem o centro dentro, de qualquer canto", () => {
  const anns = [box(1, [0, 0, 10, 10]), box(2, [20, 0, 10, 10]), box(3, [8, 8, 30, 30])];
  const rect = rectFromCorners({ x: 32, y: 12 }, { x: -1, y: -1 });
  assert.deepEqual(rect, { x: -1, y: -1, w: 33, h: 13 });
  // a 3 encosta no retângulo, mas o centro (23, 23) fica fora
  assert.deepEqual(idsInRect(anns, rect), [1, 2]);
});

test("cada caixa do bloco para na borda sozinha; as outras continuam andando", () => {
  // Bug: uma caixa encostada na borda direita travava o bloco inteiro.
  assert.deepEqual(boxDelta([170, 10, 30, 20], 15, 5, 200, 100), { dx: 0, dy: 5 });
  assert.deepEqual(boxDelta([10, 10, 20, 20], 15, 5, 200, 100), { dx: 15, dy: 5 });
  assert.deepEqual(boxDelta([150, 10, 30, 20], 50, 0, 200, 100), { dx: 20, dy: 0 });
  assert.deepEqual(boxDelta([5, 5, 20, 20], -50, -50, 200, 100), { dx: -5, dy: -5 });
});

test("caixa do tamanho da imagem não anda, mas não trava as outras", () => {
  assert.deepEqual(boxDelta([0, 0, 200, 100], 10, 10, 200, 100), { dx: 0, dy: 0 });
  assert.deepEqual(boxDelta([0, 0, 200, 100], -10, -10, 200, 100), { dx: 0, dy: 0 });
});

test("caixa que já passa da borda não é empurrada para dentro nem sai mais", () => {
  // OBB girada pode ter o envelope além da imagem.
  assert.deepEqual(boxDelta([190, 10, 30, 20], -5, 0, 200, 100), { dx: -5, dy: 0 });
  assert.deepEqual(boxDelta([190, 10, 30, 20], 5, 0, 200, 100), { dx: 0, dy: 0 });
});

test("mover: caixa e OBB pela bbox; keypoint pelos pontos marcados", () => {
  assert.deepEqual(movedPatch(box(1, [1, 2, 3, 4]), 5, -1), { bbox: [6, 1, 3, 4] });
  const kp = box(2, [0, 0, 1, 1], { keypoints: [[10, 10, 2], [0, 0, 0]] });
  assert.deepEqual(movedPatch(kp, 1, 2), { keypoints: [[11, 12, 2], [0, 0, 0]] });
});

test("desfazer o movimento devolve a geometria original no formato do PATCH", () => {
  const obb = { cx: 5, cy: 5, width: 4, height: 2, angle: 30 };
  assert.deepEqual(beforeMovePatch(box(1, [1, 2, 3, 4], { obb })), { obb });
  assert.deepEqual(beforeMovePatch(box(1, [1, 2, 3, 4])), { bbox: [1, 2, 3, 4] });
});

test("colar copia classe, geometria e ID; descarta o que já estava fora da imagem", () => {
  const clip = {
    width: 100,
    height: 100,
    rotation: 0 as const,
    annotations: [box(1, [10, 10, 5, 5], { category_id: 1, track_id: 7, score: 0.9, source: "model" }), box(2, [500, 500, 5, 5])],
  };
  const { annotations, skipped } = pastePayload(clip, { width: 100, height: 100, rotation: 0 });
  assert.equal(skipped, 1);
  assert.deepEqual(annotations, [{ category_id: 1, bbox: [10, 10, 5, 5], source: "manual", track_id: 7 }]);
});

test("colar numa imagem de outro tamanho mantém a posição relativa (bug: caixas fora da imagem)", () => {
  // Copiado de uma imagem 2000×1000, colado numa de 1000×500: tudo cabe, na mesma proporção.
  const clip = { width: 2000, height: 1000, rotation: 0 as const, annotations: [box(1, [1800, 800, 100, 100]), box(2, [200, 100, 400, 50])] };
  const { annotations, skipped } = pastePayload(clip, { width: 1000, height: 500, rotation: 0 });
  assert.equal(skipped, 0);
  assert.deepEqual(annotations.map((a) => a.bbox), [[900, 400, 50, 50], [100, 50, 200, 25]]);
});

const space = (width: number, height: number, rotation: 0 | 90 | 180 | 270 = 0) => ({ width, height, rotation });
const round = (xs: number[]) => xs.map((v) => Math.round(v * 1000) / 1000 || 0);

test("escala leva OBB e keypoints junto; sem mudança de tamanho nem rotação, a anotação fica igual", () => {
  const obb = { cx: 100, cy: 50, width: 40, height: 10, angle: 0 };
  const scaled = transformAnnotation(box(1, [80, 45, 40, 10], { obb, keypoints: [[10, 20, 2]] }), space(200, 100), space(100, 50));
  const o = scaled.obb!;
  assert.deepEqual(round([o.cx, o.cy, o.width, o.height, o.angle]), [50, 25, 20, 5, 0]);
  assert.deepEqual(scaled.keypoints, [[5, 10, 2]]);
  const same = box(2, [1, 2, 3, 4]);
  assert.equal(transformAnnotation(same, space(10, 10), space(10, 10)), same);
});

test("colar acompanha a rotação: copiado em pé, colado num documento deitado lido em 90°", () => {
  // Origem 1000×500 em pé (0°); destino é o mesmo documento deitado no arquivo (500×1000),
  // lido com a exibição girada 90°. Na tela, o campo aparece no mesmo lugar.
  // Em 90° horário, o canto superior esquerdo da tela é o inferior esquerdo da imagem.
  const field = box(1, [100, 50, 300, 40]);
  const moved = transformAnnotation(field, space(1000, 500, 0), space(500, 1000, 90));
  assert.deepEqual(round(moved.bbox), [50, 600, 40, 300]);
});

test("ida e volta entre rotações devolve a mesma caixa", () => {
  const field = box(1, [100, 50, 300, 40]);
  for (const r of [90, 180, 270] as const) {
    const dst = r === 180 ? space(1000, 500, r) : space(500, 1000, r);
    const back = transformAnnotation(transformAnnotation(field, space(1000, 500, 0), dst), dst, space(1000, 500, 0));
    assert.deepEqual(round(back.bbox), [100, 50, 300, 40], `r=${r}`);
  }
});

test("rotação leva OBB (ângulo soma a diferença) e keypoints", () => {
  const obb = { cx: 200, cy: 100, width: 80, height: 20, angle: 0 };
  const ann = box(1, [160, 90, 80, 20], { obb, keypoints: [[200, 100, 2], [0, 0, 0]] });
  // Mesma imagem quadrada, origem em 0° e destino exibido em 90°. O centro aparecia no alto
  // e no meio da tela (0,5; 0,25); em 90° esse lugar da tela mostra o ponto (100, 200).
  const moved = transformAnnotation(ann, space(400, 400, 0), space(400, 400, 90));
  const o = moved.obb!;
  assert.deepEqual(round([o.cx, o.cy, o.width, o.height]), [100, 200, 80, 20]);
  assert.equal(Math.round(Math.abs(o.angle)), 90);
  assert.deepEqual(moved.keypoints, [[100, 200, 2], [0, 400, 0]]);
});
