// Redimensionar caixa pelas alças. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { bboxFromScreen, boundResize } from "../src/features/annotate/canvas/resize.ts";

const area = { x: 100, y: 50, w: 400, h: 200 }; // imagem na tela
const old = { x: 150, y: 80, width: 100, height: 50, rotation: 0 };

test("estender e reduzir dentro da imagem passa direto", () => {
  const bigger = { ...old, width: 180, height: 90 };
  assert.deepEqual(boundResize(old, bigger, area, 2), bigger);
  const smaller = { ...old, x: 170, width: 30 };
  assert.deepEqual(boundResize(old, smaller, area, 2), smaller);
});

test("alça puxada para fora da imagem é recortada na borda", () => {
  const out = { ...old, x: 60, width: 190, height: 400 };
  assert.deepEqual(boundResize(old, out, area, 2), { ...old, x: 100, width: 150, height: 170 });
});

test("caixa menor que o mínimo ou virada do avesso mantém a anterior", () => {
  assert.deepEqual(boundResize(old, { ...old, width: 1 }, area, 2), old);
  assert.deepEqual(boundResize(old, { ...old, width: -20 }, area, 2), old);
});

test("caixa da tela vira bbox em px da imagem, com zoom", () => {
  const fit = { offsetX: -200, offsetY: 30, scale: 2.5 };
  assert.deepEqual(bboxFromScreen({ x: 50, y: 80, width: 25, height: 10 }, fit), [100, 20, 10, 4]);
});
