import { Upload, Sparkles } from "lucide-react";

export default function ModelSourceSelector({ value, onChange, disabled }: {
  value: "imported" | "catalog"; onChange: (source: "imported" | "catalog") => void; disabled: boolean;
}) {
  return <div className="model-source-selector" role="radiogroup" aria-label="Origem do modelo">
    {([
      { id: "imported", label: "Modelo importado", Icon: Upload },
      { id: "catalog", label: "Fundacional / público", Icon: Sparkles },
    ] as const).map(({ id, label, Icon }) => <button type="button" key={id} role="radio" aria-checked={value === id}
      disabled={disabled} className={`model-source-option ${value === id ? "model-source-selected" : ""}`} onClick={() => onChange(id)}
      onKeyDown={(event) => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          event.preventDefault();
          const next = event.key === "Home" ? "imported" : event.key === "End" ? "catalog" : value === "imported" ? "catalog" : "imported";
          onChange(next);
          const group = event.currentTarget.parentElement;
          const index = next === "imported" ? 0 : 1;
          (group?.querySelectorAll<HTMLButtonElement>("button")[index])?.focus();
        }
      }}>
      <Icon size={18} strokeWidth={1.75} aria-hidden="true" /><span>{label}</span>
    </button>)}
  </div>;
}
