import { useState } from "react";
import type Konva from "konva";
import type { Annotation, TaskMode } from "../../../shared/api/types";
import type { Tool } from "../store";
import { idsInRect, rectFromCorners } from "../store/selection";
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
  /** Shift+clique: liga/desliga a anotação na seleção. */
  onToggleSelect: (annId: number) => void;
  /** Retângulo de seleção: `additive` (Shift) soma à seleção atual. */
  onSelectMany: (ids: number[], additive: boolean) => void;
  onPlacePoint: (x: number, y: number) => void;
  onSelectPoint: (annId: number, index: number) => void;
}

/** Menor caixa movida ao arrastar menos que isso (px de tela) é tratada como clique. */
const MIN_DRAG_PX = 5;

/**
 * Gestos do mouse no canvas: desenhar caixa (B), selecionar (V ou clique), e no modo
 * keypoint marcar pontos (B) ou selecionar ponto (V). Com V, Shift+clique soma ou tira
 * da seleção e arrastar num espaço vazio seleciona o que estiver dentro do retângulo.
 */
export function useCanvasPointer(o: Options) {
  const [drawing, setDrawing] = useState<DrawingRect | null>(null);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  /** Retângulo de seleção (ferramenta V arrastando num espaço vazio), em px de tela. */
  const [marquee, setMarquee] = useState<{ start: { x: number; y: number }; rect: DrawingRect; additive: boolean } | null>(null);

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
    setMarquee(null);
  };

  /** Ferramenta V: Shift+clique alterna; clique em vazio começa o retângulo de seleção. */
  const startSelect = (pos: { x: number; y: number }, shift: boolean, hit: Annotation | null) => {
    if (hit) {
      if (shift) o.onToggleSelect(hit.id);
      else o.onSelect(hit.id);
      return;
    }
    if (!shift) o.onSelect(null);
    setMarquee({ start: pos, rect: { x: pos.x, y: pos.y, w: 0, h: 0 }, additive: shift });
  };

  const onMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button !== 0 || !o.hasImage || o.mode === "classification") return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    const shift = e.evt.shiftKey;
    // Shift+clique numa forma já selecionada (arrastável) a tira da seleção.
    if (shift && o.tool === "select" && (e.target.draggable() || e.target.getParent()?.draggable())) {
      const hit = annotationAt(pos.x, pos.y);
      if (hit) o.onToggleSelect(hit.id);
      return;
    }
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
      if (hit && !shift) o.onSelectPoint(hit.annId, hit.index);
      else startSelect(pos, shift, hit ? o.annotations.find((a) => a.id === hit.annId) ?? null : annotationAt(pos.x, pos.y));
      return;
    }
    if (o.tool === "select") {
      startSelect(pos, shift, annotationAt(pos.x, pos.y));
      return;
    }
    if (!o.isInsideImage(pos.x, pos.y)) return;
    setStartPos({ x: pos.x, y: pos.y });
    setDrawing({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const onMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const pos = e.target.getStage()?.getPointerPosition();
    if (marquee && pos) {
      setMarquee({ ...marquee, rect: rectFromCorners(marquee.start, pos) });
      return;
    }
    if (!startPos || !o.hasImage || o.mode === "classification") return;
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
    if (marquee) {
      const { rect, additive } = marquee;
      if (rect.w >= MIN_DRAG_PX && rect.h >= MIN_DRAG_PX) {
        const a = o.toImageCoords(rect.x, rect.y);
        const b = o.toImageCoords(rect.x + rect.w, rect.y + rect.h);
        o.onSelectMany(idsInRect(o.annotations, rectFromCorners(a, b)), additive);
      }
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

  return { drawing, marquee: marquee?.rect ?? null, annotationAt, onMouseDown, onMouseMove, onMouseUp };
}
