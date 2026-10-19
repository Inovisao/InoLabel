// Etiquetas transparentes sob o ponteiro. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { boundsOf, fadedLabelIds, labelFontSize, labelRect } from "../src/features/annotate/canvas/labelOverlap.ts";

// Duas caixas empilhadas (campos de formulário): a etiqueta da de baixo invade a de cima.
const top = { id: 1, bounds: { x: 10, y: 20, w: 200, h: 30 } };
const bottom = { id: 2, bounds: { x: 10, y: 52, w: 200, h: 30 } };
const labels = [top, bottom].map((s) => ({ id: s.id, rect: labelRect(s.bounds.x, s.bounds.y, "campo", 14) }));

test("etiqueta fica acima da forma e não sai do topo da imagem", () => {
  assert.deepEqual(labelRect(10, 52, "abc", 14), { x: 10, y: 34, w: 3 * 14 * 0.6 + 8, h: 18 });
  assert.equal(labelRect(10, 5, "abc", 14).y, 0);
  assert.equal(labelFontSize(10), 10);
  assert.equal(labelFontSize(1000), 14);
});

test("ponteiro na caixa de cima apaga a etiqueta da de baixo que a invade", () => {
  assert.deepEqual(fadedLabelIds(labels, { x: 150, y: 45 }, top), [2]);
});

test("ponteiro sobre a etiqueta a apaga", () => {
  assert.deepEqual(fadedLabelIds(labels, { x: 15, y: 40 }, null), [2]);
});

test("a etiqueta da própria forma, fora dela, continua visível", () => {
  assert.deepEqual(fadedLabelIds(labels, { x: 150, y: 70 }, bottom), []);
});

test("sem ponteiro ou longe das etiquetas nada some", () => {
  assert.deepEqual(fadedLabelIds(labels, null, top), []);
  assert.deepEqual(fadedLabelIds(labels, { x: 500, y: 500 }, null), []);
});

test("contorno de OBB na tela é o retângulo dos cantos", () => {
  assert.deepEqual(boundsOf([[10, 5], [30, 15], [20, 40], [0, 25]]), { x: 0, y: 5, w: 30, h: 35 });
});
