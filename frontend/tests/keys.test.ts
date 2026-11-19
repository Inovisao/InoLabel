// Atalhos de mouse e tecla de segurar. Rodar: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { DEFAULT_BINDS, freshDefaults, withDefaults } from "../src/features/keybinds/defaults.ts";
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

test("perfil sem alguma ação (versão antiga ou outro backend) recebe o padrão dela", () => {
  // Bug: binds.<ação> indefinido derrubava a tela de anotação (página em branco).
  const partial = { ...freshDefaults(), tool_box: ["G"] } as Record<string, string[]>;
  delete partial.rotate_view_cw;
  const fixed = withDefaults({ active_profile: "Meu", profiles: { "Meu": partial as never } });
  assert.deepEqual(fixed.profiles["Meu"].rotate_view_cw, DEFAULT_BINDS.rotate_view_cw);
  assert.deepEqual(fixed.profiles["Meu"].tool_box, ["G"]);
  assert.ok(fixed.profiles["Padrão"]);
});

test("perfil ativo inexistente volta ao Padrão", () => {
  assert.equal(withDefaults({ active_profile: "Sumiu", profiles: {} }).active_profile, "Padrão");
});
