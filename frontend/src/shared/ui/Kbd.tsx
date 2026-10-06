/** Tecla de atalho exibida ao lado de um item (ex.: "B", "Ctrl+Z"). */
export default function Kbd({ children }: { children: string }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontFamily: "var(--font-mono)",
        color: "var(--color-muted)",
        background: "var(--color-neutral)",
        border: "1px solid var(--color-border)",
        borderRadius: 4,
        padding: "1px 5px",
        flexShrink: 0,
      }}
    >
      {children}
    </span>
  );
}
