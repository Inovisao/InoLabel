import { useEffect, useRef, useState, type Dispatch, type RefObject, type SetStateAction } from "react";
import type { Binds } from "../../keybinds/defaults";
import { baseKey, dragForEvent, keyForEvent, matches, matchesGesture, wheelForEvent } from "../../keybinds/keys";
import { panBy, wheelPixels, wheelZoomFactor, zoomAt, type View, type ViewBase } from "./viewport";

const isTyping = (target: EventTarget | null) => {
  const el = target as HTMLElement | null;
  if (!el?.tagName) return false;
  return ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable;
};

interface Options {
  containerRef: RefObject<HTMLDivElement | null>;
  base: ViewBase;
  binds: Binds;
  view: View | null;
  setView: Dispatch<SetStateAction<View | null>>;
  /** Muda a cada frame: a vista volta ao ajuste. */
  resetKey: unknown;
}

/**
 * Zoom e pan do canvas pelos atalhos do perfil ativo. Os ouvintes ficam no container
 * do canvas, então a roda com Ctrl só deixa de ser o zoom do navegador sobre a imagem.
 * O pan intercepta o clique antes do Konva (fase de captura): não desenha nem arrasta
 * forma.
 */
export function useCanvasViewport({ containerRef, base, binds, view, setView, resetKey }: Options) {
  const [panReady, setPanReady] = useState(false);
  const [panning, setPanning] = useState(false);
  // Os ouvintes nativos leem o estado atual sem serem religados a cada render.
  const baseRef = useRef(base);
  const bindsRef = useRef(binds);
  const viewRef = useRef(view);
  const holdRef = useRef(false);
  baseRef.current = base;
  bindsRef.current = binds;
  viewRef.current = view;

  useEffect(() => setView(null), [resetKey, setView]);

  // Teclado: ajustar à tela e segurar a tecla para mover com o botão esquerdo.
  useEffect(() => {
    const release = () => {
      holdRef.current = false;
      setPanReady(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (isTyping(e.target)) return;
      if (matches(e, bindsRef.current, "zoom_fit")) {
        e.preventDefault();
        setView(null);
      } else if (matches(e, bindsRef.current, "pan_hold")) {
        e.preventDefault();
        holdRef.current = true;
        setPanReady(true);
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      const key = keyForEvent(e);
      if (key && bindsRef.current.pan_hold.some((bound) => baseKey(bound) === baseKey(key))) release();
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", release);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", release);
    };
  }, [setView]);

  // Mouse: roda (zoom ou rolagem) e arraste para mover a imagem.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let last: { x: number; y: number } | null = null;

    const onWheel = (e: WheelEvent) => {
      const b = baseRef.current;
      if (!b.imgW) return;
      if (matchesGesture(wheelForEvent(e), bindsRef.current, "zoom_wheel")) {
        e.preventDefault();
        // Com uma caixa em desenho o retângulo está em px de tela; não muda a escala no meio.
        if (e.buttons & 1) return;
        const rect = el.getBoundingClientRect();
        const factor = wheelZoomFactor(wheelPixels(e.deltaY || e.deltaX, e.deltaMode));
        setView((v) => zoomAt(v, b, e.clientX - rect.left, e.clientY - rect.top, factor));
        return;
      }
      // Sem o gesto de zoom, a roda rola a imagem ampliada (Shift: na horizontal).
      if (!viewRef.current) return;
      e.preventDefault();
      const sideways = e.shiftKey && !e.deltaX;
      const dx = wheelPixels(sideways ? e.deltaY : e.deltaX, e.deltaMode);
      const dy = sideways ? 0 : wheelPixels(e.deltaY, e.deltaMode);
      setView((v) => panBy(v, b, -dx, -dy));
    };

    const startsPan = (e: MouseEvent) =>
      matchesGesture(dragForEvent(e), bindsRef.current, "pan_drag") || (e.button === 0 && holdRef.current);

    const onPointerDown = (e: PointerEvent) => {
      if (e.pointerType === "touch" || !baseRef.current.imgW || !startsPan(e)) return;
      e.preventDefault();
      e.stopPropagation();
      last = { x: e.clientX, y: e.clientY };
      setPanning(true);
    };
    // O mousedown vem depois do pointerdown: também não pode chegar ao Konva, e o
    // preventDefault evita a rolagem automática do botão do meio.
    const onMouseDown = (e: MouseEvent) => {
      if (!last) return;
      e.preventDefault();
      e.stopPropagation();
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!last) return;
      const dx = e.clientX - last.x;
      const dy = e.clientY - last.y;
      last = { x: e.clientX, y: e.clientY };
      setView((v) => panBy(v, baseRef.current, dx, dy));
    };
    const onPointerUp = () => {
      if (!last) return;
      last = null;
      setPanning(false);
    };
    // Botão do meio no Linux cola a seleção; botão direito abre o menu se for o do pan.
    const onAuxClick = (e: MouseEvent) => {
      if (e.button === 1) e.preventDefault();
    };
    const onContextMenu = (e: MouseEvent) => {
      if (bindsRef.current.pan_drag.some((bound) => bound.endsWith("RightDrag"))) e.preventDefault();
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("pointerdown", onPointerDown, { capture: true });
    el.addEventListener("mousedown", onMouseDown, { capture: true });
    el.addEventListener("auxclick", onAuxClick);
    el.addEventListener("contextmenu", onContextMenu);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("blur", onPointerUp);
    return () => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("pointerdown", onPointerDown, { capture: true });
      el.removeEventListener("mousedown", onMouseDown, { capture: true });
      el.removeEventListener("auxclick", onAuxClick);
      el.removeEventListener("contextmenu", onContextMenu);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("blur", onPointerUp);
    };
  }, [containerRef, setView]);

  return { panReady, panning };
}
