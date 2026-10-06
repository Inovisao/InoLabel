import { Group, Rect } from "react-konva";
import type { Annotation } from "../../../shared/api/types";
import ShapeLabel, { labelFontSize } from "./ShapeLabel";
import type { ImageFit } from "./useImageFit";

interface Props {
  ann: Annotation;
  fit: ImageFit;
  color: string;
  label: string;
  selected: boolean;
  /** Ferramenta V com a caixa selecionada: pode arrastar. */
  movable: boolean;
  onMove: (bbox: [number, number, number, number]) => void;
  onRequestRemove: () => void;
}

/** Caixa alinhada aos eixos (detecção e rastreamento). */
export default function BoxShape({ ann, fit, color, label, selected, movable, onMove, onRequestRemove }: Props) {
  const [bx, by, bw, bh] = ann.bbox;
  const sx = fit.offsetX + bx * fit.scale;
  const sy = fit.offsetY + by * fit.scale;
  const sw = bw * fit.scale;
  const sh = bh * fit.scale;

  return (
    <Group onDblClick={onRequestRemove}>
      <Rect
        x={sx}
        y={sy}
        width={sw}
        height={sh}
        stroke={color}
        strokeWidth={selected ? 3 : 2}
        dash={selected ? [8, 4] : undefined}
        fill="transparent"
        listening={true}
        draggable={movable}
        dragBoundFunc={(p) => ({
          x: Math.max(fit.offsetX, Math.min(p.x, fit.offsetX + fit.shownW - sw)),
          y: Math.max(fit.offsetY, Math.min(p.y, fit.offsetY + fit.shownH - sh)),
        })}
        onDragEnd={(e) => {
          const nx = (e.target.x() - fit.offsetX) / fit.scale;
          const ny = (e.target.y() - fit.offsetY) / fit.scale;
          onMove([nx, ny, bw, bh]);
        }}
      />
      <ShapeLabel x={sx} y={sy} label={label} color={color} fontSize={labelFontSize(sw)} />
    </Group>
  );
}
