import { useId } from "react";
import type { ComponentType } from "react";
import type { ClassItem } from "../../../shared/api/types";
import type { InputSchema } from "../types";
import ClassPromptsControl from "./controls/ClassPromptsControl.tsx";
import { resolveSchema } from "./schema.ts";

interface ControlProps {
  value: unknown; onChange: (value: unknown) => void; classes: ClassItem[]; disabled: boolean;
}

// Register a specialized control here only when the standard fields are insufficient.
const CONTROLS: Record<string, ComponentType<ControlProps>> = { "class-prompts": ClassPromptsControl };

export default function ModelConfigForm({ schema, value, onChange, classes, disabled = false, root = schema }: {
  schema: InputSchema; value: Record<string, unknown>; onChange: (value: Record<string, unknown>) => void;
  classes: ClassItem[]; disabled?: boolean; root?: InputSchema;
}) {
  const prefix = useId();
  return <div className="model-config-form">{Object.entries(schema.properties ?? {}).map(([key, raw]) => {
    const field = resolveSchema(raw, root);
    const id = `${prefix}-${key}`;
    const change = (next: unknown) => onChange({ ...value, [key]: next });
    const Extension = field["x-control"] ? CONTROLS[field["x-control"]!] : undefined;
    return <div key={key} className="model-config-field">
      <label htmlFor={id} className="text-label">{field.title ?? key}</label>
      {field.description && <span id={`${id}-hint`} className="text-helper">{field.description}</span>}
      {Extension ? <Extension value={value[key]} onChange={change} classes={classes} disabled={disabled} />
        : field.enum ? <select id={id} className="input" disabled={disabled} value={String(value[key] ?? field.default ?? "")}
          onChange={(e) => change(field.enum!.find((option) => String(option) === e.target.value))}>
          {field.enum.map((option) => <option key={String(option)} value={String(option)}>{String(option)}</option>)}
        </select>
        : field.type === "boolean" ? <input id={id} type="checkbox" checked={value[key] === true} disabled={disabled} onChange={(e) => change(e.target.checked)} />
        : field.type === "number" || field.type === "integer" ? <input id={id} className="input" type="number" disabled={disabled}
          min={field.minimum} max={field.maximum} step={field["x-step"] ?? (field.type === "integer" ? 1 : "any")}
          value={typeof value[key] === "number" ? Number(value[key]) : ""} onChange={(e) => change(e.target.value === "" ? "" : Number(e.target.value))} />
        : field.type === "string" ? <textarea id={id} className="input" disabled={disabled} maxLength={field.maxLength}
          value={String(value[key] ?? "")} onChange={(e) => change(e.target.value)} style={{ minHeight: 64, padding: 10 }} />
        : field.type === "object" ? <ModelConfigForm schema={field} root={root} value={(value[key] ?? {}) as Record<string, unknown>}
          onChange={change} classes={classes} disabled={disabled} />
        : <span role="alert">Este tipo de entrada requer um controle de interface registrado.</span>}
    </div>;
  })}</div>;
}
