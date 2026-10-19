import { useEffect, useRef } from "react";
import Konva from "konva";
import { Group, Rect, Text } from "react-konva";
import { labelRect } from "./labelOverlap";
import type { Rotation } from "./viewRotation";

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
  /** Exibição girada: a etiqueta gira ao contrário para o texto ficar em pé na tela. */
  rotation?: Rotation;
}

/** Etiqueta da classe acima da forma (fundo na cor da forma, texto branco). */
export default function ShapeLabel({ x, y, label, color, fontSize, faded = false, rotation = 0 }: Props) {
  // Desenhada num grupo em (x, y): sem rotação, presa ao topo do canvas como antes; girada,
  // o grupo é contra-rotacionado e a etiqueta fica logo acima do ponto, em pé.
  const rect = labelRect(x, y, label, fontSize);
  const rectY = rotation ? -fontSize - 4 : rect.y - y;
  const textY = rotation ? -fontSize - 1 : Math.max(2, y - fontSize - 1) - y;
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
    <Group x={x} y={y} rotation={-rotation} listening={false}>
      <Rect
        ref={backgroundRef}
        x={0}
        y={rectY}
        width={rect.w}
        height={rect.h}
        fill={color}
        cornerRadius={3}
        listening={false}
      />
      <Text
        ref={textRef}
        x={4}
        y={textY}
        text={label}
        fontSize={fontSize}
        fontFamily="Inter, sans-serif"
        fontStyle="600"
        fill="#fff"
        listening={false}
      />
    </Group>
  );
}

