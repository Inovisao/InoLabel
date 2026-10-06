import { useCallback, useEffect, useRef, useState } from "react";

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
}

/**
 * Carrega a imagem do frame e a encaixa no container (mantém a proporção, centraliza).
 * `onImageSize` recebe o tamanho real quando a imagem carrega.
 */
export function useImageFit(imageB64: string | undefined, onImageSize: (size: { width: number; height: number }) => void) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [img, setImg] = useState<HTMLImageElement | null>(null);

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
      onImageSize({ width: image.width, height: image.height });
    };
  }, [imageB64]); // eslint-disable-line react-hooks/exhaustive-deps

  const scale = img ? Math.min(size.width / img.width, size.height / img.height) : 1;
  const shownW = img ? img.width * scale : 0;
  const shownH = img ? img.height * scale : 0;
  const fit: ImageFit = {
    scale,
    offsetX: (size.width - shownW) / 2,
    offsetY: (size.height - shownH) / 2,
    shownW,
    shownH,
    imgW: img?.width ?? 0,
    imgH: img?.height ?? 0,
  };

  /** Tela → pixels da imagem, presos aos limites da imagem. */
  const toImageCoords = useCallback(
    (stageX: number, stageY: number) => ({
      x: Math.max(0, Math.min((stageX - fit.offsetX) / scale, fit.imgW)),
      y: Math.max(0, Math.min((stageY - fit.offsetY) / scale, fit.imgH)),
    }),
    [fit.offsetX, fit.offsetY, scale, fit.imgW, fit.imgH]
  );

  const isInsideImage = (x: number, y: number) =>
    x >= fit.offsetX && x <= fit.offsetX + shownW && y >= fit.offsetY && y <= fit.offsetY + shownH;

  return { containerRef, size, img, fit, toImageCoords, isInsideImage };
}
