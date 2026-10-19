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
  /** Etiqueta transparente (ponteiro sobre ela ou sobre a forma que ela invade). */
  labelFaded?: boolean;
  /** Parte de um bloco selecionado sendo arrastado por outra caixa (px de tela). */
  groupOffset?: { dx: number; dy: number };
  /** Bloco: arrastar esta caixa move a seleção inteira (delta em px de tela). */
  onGroupDragMove?: (dx: number, dy: number) => void;
  onGroupDragEnd?: (dx: number, dy: number) => void;
}

/** Caixa alinhada aos eixos (detecção e rastreamento). */
export default function BoxShape({
  ann, fit, color, label, selected, movable, onMove, onRequestRemove, labelFaded,
  groupOffset, onGroupDragMove, onGroupDragEnd,
}: Props) {
  const [bx, by, bw, bh] = ann.bbox;
  const sx = fit.offsetX + bx * fit.scale + (groupOffset?.dx ?? 0);
  const sy = fit.offsetY + by * fit.scale + (groupOffset?.dy ?? 0);
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
        onDragMove={(e) => onGroupDragMove?.(e.target.x() - sx, e.target.y() - sy)}
        onDragEnd={(e) => {
          if (onGroupDragEnd) {
            const [dx, dy] = [e.target.x() - sx, e.target.y() - sy];
            // Volta ao lugar: o bloco inteiro é desenhado deslocado até o backend responder.
            e.target.position({ x: sx, y: sy });
            onGroupDragEnd(dx, dy);
            return;
          }
          const nx = (e.target.x() - fit.offsetX) / fit.scale;
          const ny = (e.target.y() - fit.offsetY) / fit.scale;
          onMove([nx, ny, bw, bh]);
        }}
      />
      <ShapeLabel x={sx} y={sy} label={label} color={color} fontSize={labelFontSize(sw)} faded={labelFaded} />
    </Group>
  );
}
