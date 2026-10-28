import type { InputSchema } from "../types";

export function resolveSchema(schema: InputSchema, root: InputSchema): InputSchema {
  if (!schema.$ref) return schema;
  const prefix = "#/$defs/";
  return schema.$ref.startsWith(prefix) ? { ...root.$defs?.[schema.$ref.slice(prefix.length)], ...schema } : {};
}

export function schemaDefaults(schema: InputSchema, root = schema): Record<string, unknown> {
  return Object.fromEntries(Object.entries(schema.properties ?? {}).map(([key, raw]) => {
    const field = resolveSchema(raw, root);
    return [key, field.default !== undefined ? structuredClone(field.default) : field.type === "array" ? [] : field.type === "object" ? schemaDefaults(field, root) : ""];
  }));
}

export function inputErrors(schema: InputSchema, values: Record<string, unknown>, root = schema): string[] {
  const errors: string[] = [];
  for (const [key, raw] of Object.entries(schema.properties ?? {})) {
    const field = resolveSchema(raw, root);
    const value = values[key];
    const label = field.title ?? key;
    if (value === undefined && !schema.required?.includes(key)) continue;
    if (value === undefined) { errors.push(`${label}: obrigatório.`); continue; }
    if (field.type === "string" && (typeof value !== "string" || value.trim().length < (field.minLength ?? 0) || value.length > (field.maxLength ?? Infinity))) errors.push(`${label}: texto inválido.`);
    if ((field.type === "number" || field.type === "integer") && (typeof value !== "number" || !Number.isFinite(value) || value < (field.minimum ?? -Infinity) || value > (field.maximum ?? Infinity) || (field.type === "integer" && !Number.isInteger(value)))) errors.push(`${label}: número inválido.`);
    if (field.type === "boolean" && typeof value !== "boolean") errors.push(`${label}: opção inválida.`);
    if (field.enum && !field.enum.includes(value as string | number | boolean)) errors.push(`${label}: opção inválida.`);
    if (field.type === "array") {
      if (!Array.isArray(value) || value.length < (field.minItems ?? 0) || value.length > (field.maxItems ?? Infinity)) errors.push(`${label}: selecione uma quantidade válida de itens.`);
      else if (field.items) for (const item of value) {
        const nested = resolveSchema(field.items, root);
        if (nested.type === "object") {
          if (!item || typeof item !== "object" || Array.isArray(item)) errors.push(`${label}: item inválido.`);
          else errors.push(...inputErrors(nested, item as Record<string, unknown>, root));
        }
      }
    }
    if (field.type === "object") {
      if (!value || typeof value !== "object" || Array.isArray(value)) errors.push(`${label}: configuração inválida.`);
      else errors.push(...inputErrors(field, value as Record<string, unknown>, root));
    }
  }
  return errors;
}
