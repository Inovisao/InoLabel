import { isSplitValid, splitTotal } from "../split";
import type { SplitValues } from "../types";
import CheckboxRow, { subPanel } from "./CheckboxRow";

interface Props {
  enabled: boolean;
  onEnabled: (enabled: boolean) => void;
  split: SplitValues;
  onAdjust: (key: keyof SplitValues, value: number) => void;
  disabled: boolean;
}

/** Divisão em train/val/test por sliders que sempre somam 100%. */
export default function SplitSection({ enabled, onEnabled, split, onAdjust, disabled }: Props) {
  const valid = isSplitValid(split);
  return (
    <div>
      <CheckboxRow label="Dividir em train / val / test" checked={enabled} disabled={disabled} onChange={onEnabled} />
      {enabled && (
        <div style={{ ...subPanel, marginTop: 12, padding: "14px 16px", gap: 10 }}>
          <SplitRow label="Train" value={split.train} onChange={(v) => onAdjust("train", v)} disabled={disabled} />
          <SplitRow label="Val" value={split.val} onChange={(v) => onAdjust("val", v)} disabled={disabled} />
          <SplitRow label="Test" value={split.test} onChange={(v) => onAdjust("test", v)} disabled={disabled} />
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              fontSize: 11,
              color: valid ? "var(--color-muted)" : "var(--color-danger)",
              marginTop: 2,
            }}
          >
            Total: {splitTotal(split)}% {!valid && "— deve somar 100%"}
          </div>
        </div>
      )}
    </div>
  );
}

function SplitRow({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  const side = { fontSize: 12, fontWeight: 600, textAlign: "right" as const, flexShrink: 0 };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ ...side, width: 36, color: "var(--color-muted)" }}>{label}</span>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ flex: 1, accentColor: "var(--color-primary)", cursor: disabled ? "not-allowed" : "pointer" }}
      />
      <span style={{ ...side, width: 38, color: "var(--color-text)" }}>{value}%</span>
    </div>
  );
}
