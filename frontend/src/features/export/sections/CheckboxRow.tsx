interface Props {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}

/** Caixa de seleção com rótulo, no padrão das opções do export. */
export default function CheckboxRow({ label, checked, disabled, onChange }: Props) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        cursor: disabled ? "not-allowed" : "pointer",
        userSelect: "none",
      }}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        style={{ accentColor: "var(--color-primary)", width: 14, height: 14, cursor: "inherit" }}
      />
      <span className="text-label">{label}</span>
    </label>
  );
}

/** Caixa com fundo para as opções que abrem abaixo de um checkbox. */
export const subPanel = {
  padding: "12px 14px",
  background: "var(--color-bg)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-md)",
  display: "flex",
  flexDirection: "column" as const,
};
