import { useEffect, useState } from "react";
import type { Annotation, OBBGeometry } from "../../../shared/api/types";
import { useAnnotationStore } from "../store";

const rounded = (angle: number) => String(Math.round(angle * 10) / 10);

/** Modo OBB: ângulo da caixa selecionada, editável (Q/E também giram). */
export default function AngleField({ ann }: { ann: Annotation & { obb: OBBGeometry } }) {
  const rotateSelected = useAnnotationStore((s) => s.rotateSelected);
  const [text, setText] = useState(rounded(ann.obb.angle));

  useEffect(() => setText(rounded(ann.obb.angle)), [ann.id, ann.obb.angle]);

  const commit = () => {
    const value = Number(text.replace(",", "."));
    if (text.trim() === "" || !Number.isFinite(value)) setText(rounded(ann.obb.angle));
    else if (value !== ann.obb.angle) rotateSelected({ angle: value });
  };

  return (
    <>
      <label className="text-helper" htmlFor="sel-angle">Ângulo (°) · Q / E giram 5°, Shift 1°</label>
      <input
        id="sel-angle"
        className="input text-mono"
        inputMode="decimal"
        value={text}
        onChange={(e) => setText(e.target.value.replace(/[^\d.,-]/g, ""))}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        style={{ height: 32, fontSize: 13 }}
      />
    </>
  );
}
