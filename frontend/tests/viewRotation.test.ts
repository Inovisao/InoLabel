// Girar a exibição em 90°: conversões tela ↔ espaço local. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  labelAnchor, layerTransform, localSize, localToScreen, rotateBy, screenToLocal, vectorToLocal, vectorToScreen,
  type Rotation,
} from "../src/features/annotate/canvas/viewRotation.ts";

const W = 800, H = 600;
const ALL: Rotation[] = [0, 90, 180, 270];

test("girar dá a volta em passos de 90° nos dois sentidos", () => {
  assert.equal(rotateBy(270, 90), 0);
  assert.equal(rotateBy(0, -90), 270);
  assert.equal(rotateBy(90, 90), 180);
});

test("em 90° e 270° o espaço local troca largura e altura", () => {
  assert.deepEqual(localSize(W, H, 90), { width: H, height: W });
  assert.deepEqual(localSize(W, H, 180), { width: W, height: H });
  assert.deepEqual(layerTransform(W, H, 90), { x: 400, y: 300, offsetX: 300, offsetY: 400, rotation: 90 });
});

test("tela → local → tela volta ao mesmo ponto em todas as rotações", () => {
  for (const r of ALL) {
    const p = { x: 123, y: 456 };
    assert.deepEqual(localToScreen(screenToLocal(p, W, H, r), W, H, r), p, `r=${r}`);
  }
});

test("90° horário: o canto superior esquerdo local vai para o superior direito da tela", () => {
  // espaço local 600×800 centrado no canvas 800×600
  assert.deepEqual(localToScreen({ x: 0, y: 0 }, W, H, 90), { x: 800, y: 0 });
  assert.deepEqual(vectorToScreen({ x: 1, y: 0 }, 90), { x: 0, y: 1 });
});

test("Alt+→ na tela move para a direita da tela mesmo com a imagem girada", () => {
  for (const r of ALL) assert.deepEqual(vectorToScreen(vectorToLocal({ x: 10, y: 0 }, r), r), { x: 10, y: 0 });
  assert.deepEqual(vectorToLocal({ x: 10, y: 0 }, 90), { x: 0, y: -10 });
});

test("etiqueta fica no canto superior esquerdo da forma na tela", () => {
  const box: [number, number][] = [[100, 100], [200, 100], [200, 150], [100, 150]];
  assert.deepEqual(labelAnchor(box, W, H, 0), { screen: { x: 100, y: 100 }, local: { x: 100, y: 100 } });
  const rotated = labelAnchor(box, W, H, 90);
  // em 90° o canto da tela vem do canto inferior esquerdo local
  assert.deepEqual(rotated.local, { x: 100, y: 150 });
});
