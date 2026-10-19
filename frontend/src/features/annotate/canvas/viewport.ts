/**
 * Zoom e pan do canvas, sem React: funções puras sobre a vista atual.
 * A vista `null` é a imagem ajustada à tela (o estado ao abrir cada frame).
 */

/** Container e imagem: o necessário para ajustar e limitar a vista. */
export interface ViewBase {
  /** Escala do ajuste à tela (px de tela por px da imagem). */
  fitScale: number;
  width: number;
  height: number;
  imgW: number;
  imgH: number;
}

/** Vista ampliada: zoom relativo ao ajuste e posição da imagem no canvas (px de tela). */
export interface View {
  zoom: number;
  offsetX: number;
  offsetY: number;
}

/** Zoom máximo: um pixel da imagem ocupa até 32 px de tela. */
export const MAX_SCREEN_PX_PER_IMAGE_PX = 32;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max));

export const maxZoom = (b: ViewBase): number => Math.max(1, MAX_SCREEN_PX_PER_IMAGE_PX / b.fitScale);

/** Imagem ajustada e centralizada. */
export function fittedView(b: ViewBase): View {
  return {
    zoom: 1,
    offsetX: (b.width - b.imgW * b.fitScale) / 2,
    offsetY: (b.height - b.imgH * b.fitScale) / 2,
  };
}

/**
 * Prende a vista ao zoom permitido e à imagem: num eixo em que a imagem é maior que o
 * canvas, ela não deixa sobra vazia; num eixo em que cabe, fica centralizada.
 */
export function clampView(v: View, b: ViewBase): View {
  const zoom = clamp(v.zoom, 1, maxZoom(b));
  const axis = (offset: number, shown: number, size: number) =>
    shown <= size ? (size - shown) / 2 : clamp(offset, size - shown, 0);
  return {
    zoom,
    offsetX: axis(v.offsetX, b.imgW * b.fitScale * zoom, b.width),
    offsetY: axis(v.offsetY, b.imgH * b.fitScale * zoom, b.height),
  };
}

/** Multiplica o zoom por `factor` mantendo parado o ponto da imagem sob (x, y). */
export function zoomAt(v: View | null, b: ViewBase, x: number, y: number, factor: number): View | null {
  if (!b.imgW || !b.imgH) return null;
  const current = v ? clampView(v, b) : fittedView(b);
  const zoom = clamp(current.zoom * factor, 1, maxZoom(b));
  if (zoom <= 1) return null;
  const ratio = zoom / current.zoom;
  return clampView({ zoom, offsetX: x - (x - current.offsetX) * ratio, offsetY: y - (y - current.offsetY) * ratio }, b);
}

/** Desloca a imagem; sem zoom não há o que mover. */
export function panBy(v: View | null, b: ViewBase, dx: number, dy: number): View | null {
  if (!v) return null;
  const current = clampView(v, b);
  return clampView({ ...current, offsetX: current.offsetX + dx, offsetY: current.offsetY + dy }, b);
}

/** Delta da roda em px (o Firefox pode mandar em linhas ou páginas). */
export function wheelPixels(delta: number, deltaMode: number): number {
  if (deltaMode === 1) return delta * 16;
  if (deltaMode === 2) return delta * 400;
  return delta;
}

/** Fator de zoom de um passo da roda: ~18% por clique do mouse, suave no touchpad. */
export function wheelZoomFactor(deltaPx: number): number {
  return Math.exp(-clamp(deltaPx, -300, 300) * 0.002);
}
