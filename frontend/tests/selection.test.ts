// Seleção em bloco, copiar/colar e mover. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Annotation } from "../src/shared/api/types.ts";
import {
  beforeMovePatch, boxDelta, idsInRect, movedPatch, pastePayload, rectFromCorners, toggleId,
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

test("colar copia classe, geometria e ID; descarta o que não cabe na imagem", () => {
  const clip = [
    box(1, [10, 10, 5, 5], { category_id: 1, track_id: 7, score: 0.9, source: "model" }),
    box(2, [500, 500, 5, 5]),
  ];
  const { annotations, skipped } = pastePayload(clip, 100, 100);
  assert.equal(skipped, 1);
  assert.deepEqual(annotations, [{ category_id: 1, bbox: [10, 10, 5, 5], source: "manual", track_id: 7 }]);
});
