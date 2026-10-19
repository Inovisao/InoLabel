import { Rect, Text } from "react-konva";
import { labelRect } from "./labelOverlap";

export { labelFontSize } from "./labelOverlap";

/** Opacidade da etiqueta com o ponteiro sobre ela ou sobre a forma que ela invade. */
const FADED_OPACITY = 0.15;

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
  const opacity = faded ? FADED_OPACITY : 1;
  return (
    <>
      <Rect
        x={rect.x}
        y={rect.y}
        width={rect.w}
        height={rect.h}
        fill={color}
        cornerRadius={3}
        opacity={opacity}
        listening={false}
      />
      <Text
        x={x + 4}
        y={Math.max(2, y - fontSize - 1)}
        text={label}
        fontSize={fontSize}
        fontFamily="Inter, sans-serif"
        fontStyle="600"
        fill="#fff"
        opacity={opacity}
        listening={false}
      />
    </>
  );
}

