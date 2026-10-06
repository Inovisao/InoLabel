import { Rect, Text } from "react-konva";

interface Props {
  x: number;
  y: number;
  label: string;
  color: string;
  fontSize: number;
}

/** Etiqueta da classe acima da forma (fundo na cor da forma, texto branco). */
export default function ShapeLabel({ x, y, label, color, fontSize }: Props) {
  return (
    <>
      <Rect
        x={x}
        y={Math.max(0, y - fontSize - 4)}
        width={label.length * fontSize * 0.6 + 8}
        height={fontSize + 4}
        fill={color}
        cornerRadius={3}
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
        listening={false}
      />
    </>
  );
}

/** Tamanho da etiqueta proporcional à largura da forma (entre 10 e 14 px). */
export function labelFontSize(shapeWidth: number) {
  return Math.max(10, Math.min(14, shapeWidth * 0.12));
}
