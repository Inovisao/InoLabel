import { useEffect, useRef, useState } from "react";
import type Konva from "konva";
import { Group, Rect, Transformer } from "react-konva";
import type { Annotation } from "../../../shared/api/types";
import { bboxFromScreen, boundResize } from "./resize";
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
  /** Única selecionada com a ferramenta V: alças nos cantos e lados para redimensionar. */
  resizable?: boolean;
  /** Grava a nova bbox (mover ou redimensionar), em px da imagem. */
  onMove: (bbox: [number, number, number, number]) => void | Promise<void>;
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
  ann, fit, color, label, selected, movable, resizable = false, onMove, onRequestRemove, labelFaded,
  groupOffset, onGroupDragMove, onGroupDragEnd,
}: Props) {
  const [bx, by, bw, bh] = ann.bbox;
  const sx = fit.offsetX + bx * fit.scale + (groupOffset?.dx ?? 0);
  const sy = fit.offsetY + by * fit.scale + (groupOffset?.dy ?? 0);
  const sw = bw * fit.scale;
  const sh = bh * fit.scale;

  const rectRef = useRef<Konva.Rect>(null);
  const transformerRef = useRef<Konva.Transformer>(null);
  // Caixa durante o redimensionamento: a etiqueta acompanha as alças.
  const [live, setLive] = useState<{ x: number; y: number; w: number } | null>(null);
  // Geometria das props mais recentes: se a gravação falhar, a caixa volta a ela.
  const latest = useRef({ x: sx, y: sy, width: sw, height: sh });
  latest.current = { x: sx, y: sy, width: sw, height: sh };

  useEffect(() => {
    if (!resizable || !transformerRef.current || !rectRef.current) return;
    transformerRef.current.nodes([rectRef.current]);
    transformerRef.current.getLayer()?.batchDraw();
  }, [resizable]);

  const finishResize = async (node: Konva.Rect) => {
    // O Transformer muda a escala; a caixa guarda o tamanho real e volta à escala 1.
    const box = { x: node.x(), y: node.y(), width: node.width() * node.scaleX(), height: node.height() * node.scaleY() };
    node.setAttrs({ ...box, scaleX: 1, scaleY: 1 });
    await onMove(bboxFromScreen(box, fit));
    // Depois do render com a bbox gravada (ou a antiga, se falhou), a caixa segue as props.
    requestAnimationFrame(() => {
      rectRef.current?.setAttrs(latest.current);
      setLive(null);
    });
  };

  return (
    <Group onDblClick={onRequestRemove}>
      <Rect
        ref={rectRef}
        x={sx}
        y={sy}
        width={sw}
        height={sh}
        stroke={color}
        strokeWidth={selected ? 3 : 2}
        // Sem isso a borda engrossa junto com a escala durante o redimensionamento.
        strokeScaleEnabled={false}
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
        onTransform={(e) => {
          const node = e.target;
          setLive({ x: node.x(), y: node.y(), w: node.width() * node.scaleX() });
        }}
        onTransformEnd={(e) => finishResize(e.target as Konva.Rect)}
      />
      <ShapeLabel
        x={live?.x ?? sx}
        y={live?.y ?? sy}
        label={label}
        color={color}
        fontSize={labelFontSize(live?.w ?? sw)}
        faded={labelFaded}
      />
      {resizable && (
        <Transformer
          ref={transformerRef}
          rotateEnabled={false}
          keepRatio={false}
          flipEnabled={false}
          ignoreStroke
          borderEnabled={false}
          anchorSize={8}
          anchorCornerRadius={2}
          // Cor fixa: no rastreamento a cor da caixa é uma variável CSS, que o canvas não lê.
          anchorStroke="#3B82F6"
          anchorFill="#fff"
          // Recorta à imagem e não deixa a caixa ficar menor que 1 px da imagem.
          boundBoxFunc={(oldBox, newBox) =>
            boundResize(
              oldBox,
              newBox,
              { x: fit.offsetX, y: fit.offsetY, w: fit.shownW, h: fit.shownH },
              Math.max(2, fit.scale)
            )
          }
        />
      )}
    </Group>
  );
}
