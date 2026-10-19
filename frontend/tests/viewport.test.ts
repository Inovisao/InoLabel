// Zoom e pan do canvas (funções puras). Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  clampView, maxZoom, MAX_SCREEN_PX_PER_IMAGE_PX, panBy, wheelPixels, wheelZoomFactor, zoomAt, type ViewBase,
} from "../src/features/annotate/canvas/viewport.ts";

// Imagem 1000×500 num canvas 800×600: ajuste 0,8, imagem exibida 800×400, centrada em y=100.
const base: ViewBase = { fitScale: 0.8, width: 800, height: 600, imgW: 1000, imgH: 500 };

/** Px da imagem sob um ponto da tela, com a vista dada. */
const imagePoint = (v: { zoom: number; offsetX: number; offsetY: number }, x: number, y: number) => ({
  x: (x - v.offsetX) / (base.fitScale * v.zoom),
  y: (y - v.offsetY) / (base.fitScale * v.zoom),
});

test("zoom mantém parado o ponto da imagem sob o cursor", () => {
  const before = { x: (300 - 0) / 0.8, y: (250 - 100) / 0.8 };
  const v = zoomAt(null, base, 300, 250, 2);
  assert.ok(v);
  assert.equal(v.zoom, 2);
  const after = imagePoint(v, 300, 250);
  assert.ok(Math.abs(after.x - before.x) < 1e-9);
  assert.ok(Math.abs(after.y - before.y) < 1e-9);
});

test("reduzir até o ajuste volta à vista ajustada (null)", () => {
  const v = zoomAt(null, base, 400, 300, 2);
  assert.equal(zoomAt(v, base, 400, 300, 0.4), null);
  assert.equal(zoomAt(null, base, 400, 300, 0.5), null);
});

test("zoom tem teto de px de tela por px da imagem", () => {
  const v = zoomAt(null, base, 400, 300, 1e6);
  assert.ok(v);
  assert.equal(v.zoom, maxZoom(base));
  assert.equal(base.fitScale * v.zoom, MAX_SCREEN_PX_PER_IMAGE_PX);
});

test("sem imagem carregada não há zoom", () => {
  assert.equal(zoomAt(null, { ...base, imgW: 0, imgH: 0 }, 10, 10, 2), null);
});

test("pan não deixa sobra vazia e centraliza o eixo em que a imagem cabe", () => {
  // Zoom 1,25: imagem 1000×500 na tela — maior que o canvas na largura, menor na altura.
  const v = clampView({ zoom: 1.25, offsetX: 0, offsetY: 0 }, base);
  assert.equal(v.offsetY, 50);
  const right = panBy(v, base, 5000, 0);
  assert.equal(right?.offsetX, 0);
  const left = panBy(v, base, -5000, 0);
  assert.equal(left?.offsetX, 800 - 1000);
  assert.equal(left?.offsetY, 50);
});

test("pan sem zoom não faz nada", () => {
  assert.equal(panBy(null, base, 10, 10), null);
});

test("roda: linhas e páginas viram px, e o fator é simétrico", () => {
  assert.equal(wheelPixels(3, 1), 48);
  assert.equal(wheelPixels(1, 2), 400);
  assert.equal(wheelPixels(100, 0), 100);
  assert.ok(wheelZoomFactor(-100) > 1);
  assert.ok(wheelZoomFactor(100) < 1);
  assert.ok(Math.abs(wheelZoomFactor(100) * wheelZoomFactor(-100) - 1) < 1e-12);
});
