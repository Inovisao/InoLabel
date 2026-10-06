import { useState } from "react";
import { Circle, Group, Line } from "react-konva";
import type { Annotation, OBBGeometry } from "../../../shared/api/types";
import { angleFromCenter, fitInsideImage, obbCorners, rotateTo } from "./obbGeometry";
import ShapeLabel, { labelFontSize } from "./ShapeLabel";
import type { ImageFit } from "./useImageFit";

/** Distância (px de tela) da alça de rotação até o lado superior da caixa. */
const ROTATE_HANDLE_OFFSET = 28;
const ROTATE_SNAP_DEG = 15;

interface Props {
  ann: Annotation & { obb: OBBGeometry };
  fit: ImageFit;
  color: string;
  label: string;
  selected: boolean;
  /** Ferramenta V com a caixa selecionada: pode arrastar. */
  movable: boolean;
  onChange: (obb: OBBGeometry) => void;
  /** Grava o ângulo final; a pré-visualização some só depois. */
  onRotateTo: (angle: number) => Promise<void>;
  onRequestRemove: () => void;
}

/**
 * Caixa orientada: polígono girado, arrastável com V e, quando selecionada, alça de
 * rotação acima do lado superior (Shift encaixa de 15° em 15°). Enquanto a alça é
 * arrastada, a rotação é só pré-visualização; o PATCH sai ao soltar.
 */
export default function ObbShape({ ann, fit, color, label, selected, movable, onChange, onRotateTo, onRequestRemove }: Props) {
  const [preview, setPreview] = useState<OBBGeometry | null>(null);
  const geometry = (selected && preview) || ann.obb;
  const points = obbCorners(geometry);
  const toStage = (x: number, y: number) => [fit.offsetX + x * fit.scale, fit.offsetY + y * fit.scale] as const;

  const scaled = points.flatMap(([px, py]) => toStage(px, py));
  const labelX = Math.min(...points.map(([px]) => toStage(px, 0)[0]));
  const labelY = Math.min(...points.map(([, py]) => toStage(0, py)[1]));

  // Alça: acima do meio do lado superior, na direção "para cima" da caixa.
  const upAngle = ((geometry.angle - 90) * Math.PI) / 180;
  const [topMidX, topMidY] = toStage((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2);
  const handleX = topMidX + Math.cos(upAngle) * ROTATE_HANDLE_OFFSET;
  const handleY = topMidY + Math.sin(upAngle) * ROTATE_HANDLE_OFFSET;
  const [centerX, centerY] = toStage(geometry.cx, geometry.cy);

  return (
    <Group
      onDblClick={onRequestRemove}
      draggable={movable}
      onDragEnd={(e) => {
        if (e.target !== e.currentTarget) return;
        const dx = e.target.x() / fit.scale;
        const dy = e.target.y() / fit.scale;
        e.target.position({ x: 0, y: 0 });
        const moved = fitInsideImage({ ...ann.obb, cx: ann.obb.cx + dx, cy: ann.obb.cy + dy }, fit.imgW, fit.imgH);
        if (moved) onChange(moved);
      }}
    >
      <Line
        points={scaled}
        closed
        stroke={color}
        strokeWidth={selected ? 3 : 2}
        dash={selected ? [8, 4] : undefined}
        fill="transparent"
        listening={true}
      />
      <ShapeLabel x={labelX} y={labelY} label={label} color={color} fontSize={labelFontSize(ann.bbox[2] * fit.scale)} />
      {selected && (
        <>
          <Line points={[topMidX, topMidY, handleX, handleY]} stroke={color} strokeWidth={1.5} listening={false} />
          <Circle
            x={handleX}
            y={handleY}
            radius={7}
            fill="#fff"
            stroke={color}
            strokeWidth={2}
            draggable
            onMouseEnter={(e) => {
              const c = e.target.getStage()?.container();
              if (c) c.style.cursor = "grab";
            }}
            onMouseLeave={(e) => {
              const c = e.target.getStage()?.container();
              if (c) c.style.cursor = "";
            }}
            onDragMove={(e) => {
              const pos = e.target.getStage()?.getPointerPosition();
              if (!pos) return;
              // +90: a alça fica no "para cima" da caixa (ângulo − 90°).
              let angle = angleFromCenter(centerX, centerY, pos.x, pos.y) + 90;
              if (e.evt.shiftKey) angle = Math.round(angle / ROTATE_SNAP_DEG) * ROTATE_SNAP_DEG;
              const next = rotateTo(ann.obb, angle, fit.imgW, fit.imgH);
              if (next) setPreview(next);
              // Mantém a alça sobre o arco, não onde o ponteiro largou.
              e.target.position({ x: handleX, y: handleY });
            }}
            onDragEnd={async (e) => {
              e.cancelBubble = true;
              if (preview) await onRotateTo(preview.angle);
              setPreview(null);
            }}
          />
        </>
      )}
    </Group>
  );
}
