import { useCallback, useEffect, useRef, useState } from "react";
import { clampView, type View, type ViewBase } from "./viewport";
import { localSize, localToScreen, screenToLocal, type Point, type Rotation } from "./viewRotation";

/** Imagem encaixada no canvas: escala e deslocamento entre pixels da imagem e da tela. */
export interface ImageFit {
  scale: number;
  offsetX: number;
  offsetY: number;
  /** Tamanho exibido (px de tela). */
  shownW: number;
  shownH: number;
  /** Tamanho real da imagem (px da imagem). */
  imgW: number;
  imgH: number;
  /** Exibição girada: as medidas acima são do espaço local (alinhado à imagem). */
  rotation: Rotation;
  /** Tamanho do canvas na tela (stage). */
  stageW: number;
  stageH: number;
}

/** Ponto da tela (stage) → espaço local da camada (onde estão a imagem e as formas). */
export const toLocal = (fit: ImageFit, p: Point): Point => screenToLocal(p, fit.stageW, fit.stageH, fit.rotation);

/** Espaço local → tela (stage). */
export const toScreen = (fit: ImageFit, p: Point): Point => localToScreen(p, fit.stageW, fit.stageH, fit.rotation);

/**
 * Carrega a imagem do frame e a encaixa no container (mantém a proporção, centraliza).
 * Com `view` (zoom), escala e posição seguem a vista. Com `rotation`, o encaixe é no
 * espaço local girado (em 90°/270° a largura e a altura do canvas trocam). `ready` diz
 * se a imagem exibida já é a de `imageB64`.
 */
export function useImageFit(imageB64: string | undefined, view: View | null = null, rotation: Rotation = 0) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  // Qual imagem (base64) está carregada: até a nova carregar, `img` ainda é a anterior.
  const [loadedB64, setLoadedB64] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!imageB64) {
      setImg(null);
      return;
    }
    const image = new window.Image();
    image.src = `data:image/jpeg;base64,${imageB64}`;
    image.onload = () => {
      setImg(image);
      setLoadedB64(imageB64);
    };
  }, [imageB64]);

  const local = localSize(size.width, size.height, rotation);
  const fitScale = img ? Math.min(local.width / img.width, local.height / img.height) : 1;
  const base: ViewBase = { fitScale, width: local.width, height: local.height, imgW: img?.width ?? 0, imgH: img?.height ?? 0 };
  const shown = view && img ? clampView(view, base) : null;
  const scale = fitScale * (shown?.zoom ?? 1);
  const shownW = img ? img.width * scale : 0;
  const shownH = img ? img.height * scale : 0;
  const fit: ImageFit = {
    scale,
    offsetX: shown?.offsetX ?? (local.width - shownW) / 2,
    offsetY: shown?.offsetY ?? (local.height - shownH) / 2,
    shownW,
    shownH,
    imgW: img?.width ?? 0,
    imgH: img?.height ?? 0,
    rotation,
    stageW: size.width,
    stageH: size.height,
  };

  /** Espaço local → pixels da imagem, presos aos limites da imagem. */
  const toImageCoords = useCallback(
    (stageX: number, stageY: number) => ({
      x: Math.max(0, Math.min((stageX - fit.offsetX) / scale, fit.imgW)),
      y: Math.max(0, Math.min((stageY - fit.offsetY) / scale, fit.imgH)),
    }),
    [fit.offsetX, fit.offsetY, scale, fit.imgW, fit.imgH]
  );

  const isInsideImage = (x: number, y: number) =>
    x >= fit.offsetX && x <= fit.offsetX + shownW && y >= fit.offsetY && y <= fit.offsetY + shownH;

  /** A imagem exibida já é a de `imageB64` (não a do frame anterior). */
  const ready = !!img && loadedB64 === imageB64;

  return { containerRef, size, img, ready, fit, base, toImageCoords, isInsideImage };
}
