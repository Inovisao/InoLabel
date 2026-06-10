import { useAnnotationStore } from "../../stores/annotation";
import { useSessionStore } from "../../stores/session";

const MODE_LABELS: Record<string, string> = {
  tracking: "Rastreamento",
  detection: "Detecção",
  obb: "OBB",
  classification: "Classificação",
};

export default function Statusbar() {
  const frame = useAnnotationStore((s) => s.frame);
  const mode = useSessionStore((s) => s.mode);
  const annCount = frame?.annotations?.length ?? 0;

  return (
    <footer
      style={{
        height: 40,
        background: "var(--color-panel)",
        borderTop: "1px solid var(--color-border)",
        display: "flex",
        alignItems: "center",
        padding: "0 16px",
        gap: 0,
        flexShrink: 0,
        userSelect: "none",
      }}
    >
      {/* Mode pill */}
      {mode && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "0 10px 0 0",
            borderRight: "1px solid var(--color-border)",
            marginRight: 12,
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: 20,
              padding: "0 8px",
              background: "var(--color-primary-light)",
              color: "var(--color-primary)",
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            {MODE_LABELS[mode] ?? mode}
          </span>
        </div>
      )}

      {frame ? (
        <>
          <StatusItem label="Frame" value={`${frame.index + 1} / ${frame.total}`} />
          <Separator />
          <StatusItem
            label="Anotações"
            value={String(annCount)}
            accent={annCount > 0}
          />
          <Separator />
          <StatusItem label="Arquivo" value={frame.filename} mono />
          {frame.is_saved !== undefined && (
            <>
              <Separator />
              <span
                style={{
                  fontSize: 11,
                  color: frame.is_saved ? "var(--color-success-icon)" : "var(--color-muted)",
                  fontWeight: frame.is_saved ? 600 : 400,
                }}
              >
                {frame.is_saved ? "● Salvo" : "○ Não salvo"}
              </span>
            </>
          )}
        </>
      ) : (
        <span style={{ fontSize: 11, color: "var(--color-muted)", fontStyle: "italic" }}>
          Aguardando frame…
        </span>
      )}

      <span
        style={{
          marginLeft: "auto",
          fontSize: 11,
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        InoLabel v2.0
      </span>
    </footer>
  );
}

function Separator() {
  return (
    <div
      style={{
        width: 1,
        height: 14,
        background: "var(--color-border)",
        margin: "0 12px",
        flexShrink: 0,
      }}
    />
  );
}

function StatusItem({
  label,
  value,
  accent,
  mono,
}: {
  label: string;
  value: string;
  accent?: boolean;
  mono?: boolean;
}) {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "var(--color-muted)", fontWeight: 500 }}>
        {label}
      </span>
      <span
        style={{
          fontSize: 11,
          fontFamily: mono ? "var(--font-mono)" : undefined,
          color: accent ? "var(--color-primary)" : "var(--color-text)",
          fontWeight: accent ? 600 : 400,
          maxWidth: 200,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </span>
    </div>
  );
}
