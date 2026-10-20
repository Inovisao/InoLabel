// Atalhos de mouse e tecla de segurar. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { DEFAULT_BINDS, freshDefaults } from "../src/features/keybinds/defaults.ts";
import {
  baseKey, conflict, dragForEvent, matchesGesture, shortcutLabel, wheelForEvent,
} from "../src/features/keybinds/keys.ts";

const mods = { ctrlKey: false, metaKey: false, altKey: false, shiftKey: false };

test("padrões: Ctrl+roda dá zoom, botão do meio move, H segura, Ctrl+0 ajusta", () => {
  assert.deepEqual(DEFAULT_BINDS.zoom_wheel, ["Ctrl+Wheel"]);
  assert.deepEqual(DEFAULT_BINDS.pan_drag, ["MiddleDrag"]);
  assert.deepEqual(DEFAULT_BINDS.pan_hold, ["H"]);
  assert.deepEqual(DEFAULT_BINDS.zoom_fit, ["Ctrl+0"]);
});

test("gestos do evento: roda e botões com modificadores (Cmd conta como Ctrl)", () => {
  assert.equal(wheelForEvent({ ...mods, ctrlKey: true }), "Ctrl+Wheel");
  assert.equal(wheelForEvent({ ...mods, metaKey: true }), "Ctrl+Wheel");
  assert.equal(wheelForEvent(mods), "Wheel");
  assert.equal(dragForEvent({ ...mods, button: 1 }), "MiddleDrag");
  assert.equal(dragForEvent({ ...mods, altKey: true, button: 0 }), "Alt+LeftDrag");
  assert.equal(dragForEvent({ ...mods, button: 3 }), null);
});

test("só o gesto do perfil aciona: roda sem Ctrl não dá zoom no padrão", () => {
  const binds = freshDefaults();
  assert.ok(matchesGesture("Ctrl+Wheel", binds, "zoom_wheel"));
  assert.ok(!matchesGesture("Wheel", binds, "zoom_wheel"));
  assert.ok(!matchesGesture(null, binds, "pan_drag"));
  binds.zoom_wheel = ["Alt+Wheel"];
  assert.ok(!matchesGesture("Ctrl+Wheel", binds, "zoom_wheel"));
});

test("rótulos em português para gestos, teclas como estão", () => {
  assert.equal(shortcutLabel("Ctrl+Wheel"), "Ctrl+Roda");
  assert.equal(shortcutLabel("MiddleDrag"), "Botão do meio");
  assert.equal(shortcutLabel("Alt+LeftDrag"), "Alt+Botão esquerdo");
  assert.equal(shortcutLabel("Ctrl+S"), "Ctrl+S");
});

test("tecla de segurar: o keyup casa sem modificadores", () => {
  assert.equal(baseKey("Ctrl+Shift+H"), "H");
  assert.equal(baseKey("H"), "H");
});

test("tecla de segurar conflita com atalhos de edição", () => {
  assert.equal(conflict(freshDefaults(), "pan_hold", "B"), "tool_box");
  assert.equal(conflict(freshDefaults(), "pan_hold", "H"), null);
});

test("Ctrl+Y refaz e não conflita com o Ctrl+Z do desfazer", () => {
  assert.deepEqual(DEFAULT_BINDS.redo, ["Ctrl+Y"]);
  const binds = freshDefaults();
  binds.redo = [];
  assert.equal(conflict(binds, "redo", "Ctrl+Y"), null);
  assert.equal(conflict(freshDefaults(), "redo", "Ctrl+Z"), "undo");
});
