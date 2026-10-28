import type { ClassItem } from "../../../../shared/api/types";

interface Prompt { class_name: string; text: string }

export default function ClassPromptsControl({ value, onChange, classes, disabled }: {
  value: unknown; onChange: (value: unknown) => void; classes: ClassItem[]; disabled: boolean;
}) {
  const prompts = (Array.isArray(value) ? value : []) as Prompt[];
  return <div className="model-class-prompts">
    {classes.map((cls) => {
      const prompt = prompts.find((p) => p.class_name === cls.name);
      return <div key={cls.id} className="model-class-prompt">
        <label><input type="checkbox" checked={!!prompt} disabled={disabled} onChange={(e) =>
          onChange(e.target.checked ? [...prompts, { class_name: cls.name, text: "" }] : prompts.filter((p) => p.class_name !== cls.name))} /> {cls.name}</label>
        {prompt && <textarea className="input" aria-label={`Descrição para ${cls.name}`} placeholder="ex.: wasp, red apple"
          style={{ minHeight: 64, padding: 10, resize: "vertical" }} value={prompt.text} maxLength={300} disabled={disabled}
          onChange={(e) => onChange(prompts.map((p) => p.class_name === cls.name ? { ...p, text: e.target.value } : p))} />}
      </div>;
    })}
    {prompts.some((p) => !classes.some((c) => c.name === p.class_name)) && <p role="alert">As classes do projeto mudaram. Remova os prompts antigos ou reconfigure o modelo.</p>}
    {prompts.some((p) => !classes.some((c) => c.name === p.class_name)) && <button type="button" className="btn-ghost" disabled={disabled}
      onClick={() => onChange(prompts.filter((p) => classes.some((c) => c.name === p.class_name)))}>Remover classes antigas</button>}
  </div>;
}
