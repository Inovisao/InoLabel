// Regras da edição de classes na anotação. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { parsePointNames, removalWarning, selectedAfterRemoval } from "../src/features/annotate/store/classEdits.ts";

test("classe ativa acompanha a remoção: as seguintes descem, a removida volta à primeira", () => {
  assert.equal(selectedAfterRemoval(3, 1), 2);
  assert.equal(selectedAfterRemoval(0, 1), 0);
  assert.equal(selectedAfterRemoval(1, 1), 0);
});

test("pontos separados por vírgula, sem vazios nem espaços", () => {
  assert.deepEqual(parsePointNames(" cabeça, ombro ,, pé "), ["cabeça", "ombro", "pé"]);
  assert.deepEqual(parsePointNames(" , "), []);
});

test("aviso de remoção diz o que será apagado", () => {
  assert.match(removalWarning("carro", 3, 2), /3 anotações da classe "carro" em 2 frames/);
  assert.match(removalWarning("carro", 1, 1), /1 anotação da classe "carro" em 1 frame /);
  assert.match(removalWarning("carro", 0, 0), /não tem anotações/);
});
