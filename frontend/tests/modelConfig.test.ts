import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ModelConfigForm from "../src/features/autolabeling/model-config/ModelConfigForm.tsx";
import ModelSourceSelector from "../src/features/autolabeling/model-config/ModelSourceSelector.tsx";
import { inputErrors, schemaDefaults } from "../src/features/autolabeling/model-config/schema.ts";
import { useAutolabelingStore } from "../src/features/autolabeling/store.ts";
import type { CatalogModel, InputSchema } from "../src/features/autolabeling/types.ts";

const schema: InputSchema = {
  type: "object", required: ["class_prompts"],
  properties: {
    class_prompts: { type: "array", title: "Descrições", minItems: 1, "x-control": "class-prompts", items: { $ref: "#/$defs/Prompt" } },
    threshold: { type: "number", title: "Score mínimo", default: .3, minimum: 0, maximum: 1 },
    device: { type: "string", title: "Dispositivo", default: "auto", enum: ["auto", "cpu"] },
  },
  $defs: { Prompt: { type: "object", required: ["class_name", "text"], properties: {
    class_name: { type: "string", minLength: 1 }, text: { type: "string", minLength: 1, maxLength: 300 },
  } } },
};

const defaults = schemaDefaults(schema);
assert.deepEqual(defaults, { class_prompts: [], threshold: .3, device: "auto" });
assert.ok(inputErrors(schema, defaults).length > 0, "an empty required class selection must not enable execution");
const parameters = { ...defaults, class_prompts: [{ class_name: "Vespa", text: "a wasp" }] };
assert.deepEqual(inputErrors(schema, parameters), []);
assert.ok(inputErrors(schema, { ...parameters, threshold: NaN }).length > 0);
assert.ok(inputErrors(schema, { ...parameters, threshold: "" }).length > 0);
assert.ok(inputErrors(schema, { ...parameters, threshold: 2 }).length > 0);
assert.ok(inputErrors(schema, { ...parameters, device: "unexpected" }).length > 0);
assert.ok(inputErrors(schema, { ...parameters, class_prompts: [{ class_name: "Vespa", text: " " }] }).length > 0);
assert.ok(inputErrors(schema, { ...parameters, class_prompts: [null] }).length > 0);
assert.deepEqual(schemaDefaults(schema).class_prompts, [], "form defaults must not share mutable collections");
const nestedSchema: InputSchema = { properties: { options: { $ref: "#/$defs/Options", title: "Opções" } },
  $defs: { Options: { type: "object", properties: { limit: { type: "integer", default: 4 } } } } };
assert.deepEqual(schemaDefaults(nestedSchema), { options: { limit: 4 } });

const html = renderToStaticMarkup(createElement(ModelConfigForm, { schema, value: parameters,
  classes: [{ id: 0, name: "Vespa" }, { id: 1, name: "Abelha" }], onChange: () => {},
}));
assert.ok(html.includes("a wasp"));
assert.ok(html.includes("Abelha"));
assert.ok(html.includes('type="checkbox"'));
assert.ok(html.includes('type="number"'));
assert.ok(html.includes('value="auto"'));

const alternate: InputSchema = { type: "object", properties: {
  instruction: { type: "string", title: "Instrução", default: "Classify this image" },
  limit: { type: "integer", title: "Limite", minimum: 1, maximum: 10, default: 3 },
  enabled: { type: "boolean", title: "Ativo", default: true },
} };
const alternateHtml = renderToStaticMarkup(createElement(ModelConfigForm, { schema: alternate,
  value: schemaDefaults(alternate), classes: [], onChange: () => {},
}));
assert.ok(alternateHtml.includes("Classify this image"), "new text fields must render without model-specific JSX");
assert.ok(alternateHtml.includes('max="10"'));
assert.ok(alternateHtml.includes('type="checkbox"'));
const sourceHtml = renderToStaticMarkup(createElement(ModelSourceSelector, { value: "catalog", disabled: false, onChange: () => {} }));
assert.ok(sourceHtml.includes('role="radiogroup"'));
assert.ok(sourceHtml.includes('aria-checked="true"'));
assert.ok(sourceHtml.includes("Modelo importado"));

const foundation: CatalogModel = { id: "demo", name: "Demo", adapter: "demo", source: "catalog", strategy: "prompt_based",
  description: "", tasks: ["detect_boxes"], schema_version: 1, input_schema: schema,
  availability: "configured", reasons: [], setup: { model_path: "" }, documentation_url: "", };
const imported: CatalogModel = { ...foundation, id: "ultralytics", adapter: "ultralytics", source: "imported", strategy: "trained_model", input_schema: {} };
const store = useAutolabelingStore;
store.getState().reset("session-a");
store.setState({ config: { adapter: "ultralytics", model_path: "/own.pt", confidence: .7, class_mapping: { car: "car" } } });
store.getState().chooseModel(foundation);
assert.deepEqual(store.getState().config.parameters, defaults);
store.setState((s) => ({ config: { ...s.config, parameters } }));
store.getState().chooseModel(imported);
assert.equal(store.getState().config.model_path, "/own.pt");
assert.equal(store.getState().config.confidence, .7);
store.getState().chooseModel(foundation);
assert.deepEqual(store.getState().config.parameters, parameters, "each model must retain its own draft");
store.getState().reset("session-b");
assert.deepEqual(store.getState().configDrafts, {}, "model prompts must not leak between projects");
