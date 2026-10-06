import Kbd from "../../../shared/ui/Kbd";

/** Item da lista de ferramentas, com o atalho ao lado. */
export default function ToolButton({
  label,
  shortcut,
  onClick,
  active,
  disabled,
}: {
  label: string;
  shortcut: string;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      className={`nav-item ${active ? "nav-item-active" : ""}`}
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 10px",
        borderRadius: "var(--radius-md)",
        border: "1px solid transparent",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.5 : 1,
        fontSize: 13,
        width: "100%",
        fontFamily: "var(--font-sans)",
        textAlign: "left",
      }}
    >
      <span>{label}</span>
      <Kbd>{shortcut}</Kbd>
    </button>
  );
}
