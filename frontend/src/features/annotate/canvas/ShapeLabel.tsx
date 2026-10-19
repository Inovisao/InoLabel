import { useEffect, useRef } from "react";
import Konva from "konva";
import { Rect, Text } from "react-konva";
import { labelRect } from "./labelOverlap";

export { labelFontSize } from "./labelOverlap";

/** Opacidade da etiqueta com o ponteiro sobre ela ou sobre a forma que ela invade. */
const FADED_OPACITY = 0.15;
/** Duração da transição de opacidade (s). */
const FADE_SECONDS = 0.18;

interface Props {
  x: number;
  y: number;
  label: string;
  color: string;
  fontSize: number;
  /** Transparente para mostrar a imagem atrás (ver labelOverlap). */
  faded?: boolean;
}

/** Etiqueta da classe acima da forma (fundo na cor da forma, texto branco). */
export default function ShapeLabel({ x, y, label, color, fontSize, faded = false }: Props) {
  const rect = labelRect(x, y, label, fontSize);
  const backgroundRef = useRef<Konva.Rect>(null);
  const textRef = useRef<Konva.Text>(null);

  // Transição suave: a opacidade é animada no nó Konva, não passada como prop
  // (a prop seria reaplicada a cada render e cortaria a animação).
  useEffect(() => {
    const opacity = faded ? FADED_OPACITY : 1;
    for (const node of [backgroundRef.current, textRef.current]) {
      if (node && node.opacity() !== opacity) node.to({ opacity, duration: FADE_SECONDS, easing: Konva.Easings.EaseInOut });
    }
  }, [faded]);

  return (
    <>
      <Rect
        ref={backgroundRef}
        x={rect.x}
        y={rect.y}
        width={rect.w}
        height={rect.h}
        fill={color}
        cornerRadius={3}
        listening={false}
      />
      <Text
        ref={textRef}
        x={x + 4}
        y={Math.max(2, y - fontSize - 1)}
        text={label}
        fontSize={fontSize}
        fontFamily="Inter, sans-serif"
        fontStyle="600"
        fill="#fff"
        listening={false}
      />
    </>
  );
}

