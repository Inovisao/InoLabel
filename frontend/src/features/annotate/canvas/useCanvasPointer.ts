import { useState } from "react";
import type Konva from "konva";
import type { Annotation, TaskMode } from "../../../shared/api/types";
import type { Tool } from "../store";
import { keypointAt } from "./KeypointLayer";
import { obbCorners, pointInPolygon } from "./obbGeometry";

export interface DrawingRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Options {
  mode: TaskMode | null;
  tool: Tool;
  annotations: Annotation[];
  hasImage: boolean;
  scale: number;
  toImageCoords: (x: number, y: number) => { x: number; y: number };
  isInsideImage: (x: number, y: number) => boolean;
  /** Tela → limites da imagem na tela (para o retângulo em desenho não sair dela). */
  clampToImage: (x: number, y: number) => { x: number; y: number };
  onDrawBox: (bbox: [number, number, number, number]) => Promise<void>;
  onSelect: (annId: number | null) => void;
  onPlacePoint: (x: number, y: number) => void;
  onSelectPoint: (annId: number, index: number) => void;
}

/** Menor caixa movida ao arrastar menos que isso (px de tela) é tratada como clique. */
const MIN_DRAG_PX = 5;

/**
 * Gestos do mouse no canvas: desenhar caixa (B), selecionar (V ou clique), e no modo
 * keypoint marcar pontos (B) ou selecionar ponto (V).
 */
export function useCanvasPointer(o: Options) {
  const [drawing, setDrawing] = useState<DrawingRect | null>(null);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);

  /** Anotação sob o ponteiro (a menor, para formas sobrepostas). No OBB, pelo polígono girado. */
  const annotationAt = (stageX: number, stageY: number): Annotation | null => {
    const { x, y } = o.toImageCoords(stageX, stageY);
    let best: Annotation | null = null;
    let bestArea = Infinity;
    for (const ann of o.annotations) {
      const obb = o.mode === "obb" ? ann.obb : null;
      const [bx, by, bw, bh] = ann.bbox;
      const hit = obb ? pointInPolygon(x, y, obbCorners(obb)) : x >= bx && x <= bx + bw && y >= by && y <= by + bh;
      const area = obb ? obb.width * obb.height : bw * bh;
      if (hit && area < bestArea) {
        best = ann;
        bestArea = area;
      }
    }
    return best;
  };

  const reset = () => {
    setDrawing(null);
    setStartPos(null);
  };

  const onMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button !== 0 || !o.hasImage || o.mode === "classification") return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    // Alça de rotação ou forma arrastável: o gesto é delas, não desenha nem seleciona.
    if (e.target.draggable() || e.target.getParent()?.draggable()) return;

    if (o.mode === "keypoint") {
      if (!o.isInsideImage(pos.x, pos.y)) return;
      const { x, y } = o.toImageCoords(pos.x, pos.y);
      if (o.tool === "box") {
        o.onPlacePoint(x, y);   // B: cada clique marca o próximo ponto da classe
        return;
      }
      // V: clique perto de um ponto seleciona instância + ponto; senão, pela bbox.
      const hit = keypointAt(o.annotations, x, y, 10 / o.scale);
      if (hit) o.onSelectPoint(hit.annId, hit.index);
      else o.onSelect(annotationAt(pos.x, pos.y)?.id ?? null);
      return;
    }
    if (o.tool === "select") {
      o.onSelect(annotationAt(pos.x, pos.y)?.id ?? null);
      return;
    }
    if (!o.isInsideImage(pos.x, pos.y)) return;
    setStartPos({ x: pos.x, y: pos.y });
    setDrawing({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const onMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!startPos || !o.hasImage || o.mode === "classification") return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    const c = o.clampToImage(pos.x, pos.y);
    setDrawing({
      x: Math.min(c.x, startPos.x),
      y: Math.min(c.y, startPos.y),
      w: Math.abs(c.x - startPos.x),
      h: Math.abs(c.y - startPos.y),
    });
  };

  const onMouseUp = async () => {
    if (o.mode === "classification") {
      reset();
      return;
    }
    if (!drawing || !startPos || drawing.w < MIN_DRAG_PX || drawing.h < MIN_DRAG_PX) {
      // Clique sem arrastar também seleciona a caixa sob o ponteiro.
      if (startPos) o.onSelect(annotationAt(startPos.x, startPos.y)?.id ?? null);
      reset();
      return;
    }
    const tl = o.toImageCoords(drawing.x, drawing.y);
    const br = o.toImageCoords(drawing.x + drawing.w, drawing.y + drawing.h);
    await o.onDrawBox([tl.x, tl.y, Math.max(1, br.x - tl.x), Math.max(1, br.y - tl.y)]);
    reset();
  };

  return { drawing, onMouseDown, onMouseMove, onMouseUp };
}
