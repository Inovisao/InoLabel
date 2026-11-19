// Cores das caixas no canvas. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { shapeStyle, TRACK_COLORS } from "../src/features/annotate/canvas/shapeStyle.ts";

const ann = (extra = {}) => ({ id: 1, image_id: 0, category_id: 0, bbox: [0, 0, 1, 1], source: "manual", ...extra }) as never;

test("cores do rastreamento são cores reais (bug: var(--…) virava preto no canvas)", () => {
  for (const c of TRACK_COLORS) assert.match(c, /^#[0-9A-F]{6}$/i);
  const { color } = shapeStyle(ann({ track_id: 3 }), undefined, "tracking");
  assert.match(color, /^#[0-9A-F]{6}$/i);
});

test("fora do rastreamento a caixa usa a cor da classe (escolhida pelo usuário)", () => {
  const cls = { id: 0, name: "carro", color: "#FF8800" };
  assert.equal(shapeStyle(ann(), cls, "detection").color, "#FF8800");
});
