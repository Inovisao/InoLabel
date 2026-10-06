import { Group, Line, Circle, Text } from "react-konva";
import { useAnnotationStore } from "../../stores/annotation";
import type { Annotation, ClassItem, Keypoint } from "../../api/types";

interface Props {
  offsetX: number;
  offsetY: number;
  scale: number;
  /** Tamanho da imagem em pixels (para prender os pontos arrastados dentro dela). */
  imgW: number;
  imgH: number;
}

const POINT_RADIUS = 4;
const FALLBACK_COLOR = "#4F46E5";

/**
 * Pares de pontos a ligar: o esqueleto da classe, ou vizinhos na ordem da classe
 * (o último volta ao primeiro com 3+ pontos). Só se desenha a ligação com os dois
 * pontos marcados — um ponto ausente interrompe a linha em vez de criar uma diagonal.
 */
function links(points: Keypoint[], skeleton: [number, number][] | undefined): [number, number][] {
  if (skeleton && skeleton.length) return skeleton;
  const chain: [number, number][] = [];
  for (let i = 0; i + 1 < points.length; i++) chain.push([i, i + 1]);
  if (points.length >= 3) chain.push([points.length - 1, 0]);
  return chain;
}

/**
 * Instâncias de keypoint no canvas: pontos (cheio = visível, vazado = oculto),
 * ligações e a instância em andamento. Com a ferramenta de seleção (V), clicar num
 * ponto seleciona a instância e o ponto; arrastar move o ponto.
 */
export default function KeypointLayer({ offsetX, offsetY, scale, imgW, imgH }: Props) {
  const { frame, classes, selectedAnnotationId, selectedKpIndex, kpWip, tool, selectKeypoint, kpMovePoint } =
    useAnnotationStore();

  const toStage = (x: number, y: number) => [offsetX + x * scale, offsetY + y * scale] as const;
  const classOf = (id: number): ClassItem | undefined => classes.find((c) => c.id === id);

  const renderInstance = (
    key: string,
    ann: Pick<Annotation, "category_id" | "keypoints"> & { id?: number },
    opts: { selected: boolean; wip: boolean }
  ) => {
    const points = ann.keypoints ?? [];
    const cls = classOf(ann.category_id);
    const color = cls?.color ?? FALLBACK_COLOR;
    const names = cls?.keypoints ?? [];
    const editable = !opts.wip && ann.id !== undefined && tool === "select";
    const marked = points.filter((p) => p[2] > 0);
    const labelAt = marked.length
      ? toStage(Math.min(...marked.map((p) => p[0])), Math.min(...marked.map((p) => p[1])))
      : null;
    const selectedPoint = opts.selected && selectedKpIndex !== null ? points[selectedKpIndex] : undefined;

    return (
      <Group key={key}>
        {links(points, cls?.skeleton).map(([a, b]) => {
          const pa = points[a];
          const pb = points[b];
          if (!pa || !pb || pa[2] <= 0 || pb[2] <= 0) return null;
          return (
            <Line
              key={`l${a}-${b}`}
              points={[...toStage(pa[0], pa[1]), ...toStage(pb[0], pb[1])]}
              stroke={color}
              strokeWidth={opts.selected ? 2.5 : 1.5}
              dash={opts.wip ? [6, 4] : undefined}
              listening={false}
            />
          );
        })}
        {points.map((p, i) => {
          if (p[2] <= 0) return null;
          const [sx, sy] = toStage(p[0], p[1]);
          const isSelectedPoint = opts.selected && selectedKpIndex === i;
          return (
            <Circle
              key={`p${i}`}
              x={sx}
              y={sy}
              radius={isSelectedPoint ? POINT_RADIUS + 3 : opts.selected ? POINT_RADIUS + 1 : POINT_RADIUS}
              // Oculto (v = 1): ponto vazado; visível (v = 2): cheio.
              fill={p[2] === 2 ? color : "#fff"}
              stroke={isSelectedPoint ? "#fff" : color}
              strokeWidth={p[2] === 2 ? 1.5 : 2}
              draggable={editable}
              dragBoundFunc={(pos) => ({
                x: Math.min(Math.max(pos.x, offsetX), offsetX + imgW * scale),
                y: Math.min(Math.max(pos.y, offsetY), offsetY + imgH * scale),
              })}
              onMouseDown={(e) => {
                if (!editable || ann.id === undefined) return;
                e.cancelBubble = true;
                selectKeypoint(ann.id, i);
              }}
              onDragEnd={(e) => {
                if (ann.id === undefined) return;
                const x = (e.target.x() - offsetX) / scale;
                const y = (e.target.y() - offsetY) / scale;
                kpMovePoint(ann.id, i, x, y);
              }}
              onMouseEnter={(e) => {
                const c = e.target.getStage()?.container();
                if (c && editable) c.style.cursor = "move";
              }}
              onMouseLeave={(e) => {
                const c = e.target.getStage()?.container();
                if (c) c.style.cursor = "";
              }}
            />
          );
        })}
        {selectedPoint && selectedPoint[2] > 0 && selectedKpIndex !== null && (
          <Text
            x={toStage(selectedPoint[0], selectedPoint[1])[0] + 8}
            y={toStage(selectedPoint[0], selectedPoint[1])[1] - 18}
            text={names[selectedKpIndex] ?? `#${selectedKpIndex + 1}`}
            fontSize={12}
            fontFamily="Inter, sans-serif"
            fontStyle="600"
            fill="#fff"
            shadowColor="#000"
            shadowBlur={3}
            listening={false}
          />
        )}
        {labelAt && !opts.wip && (
          <Text
            x={labelAt[0]}
            y={Math.max(2, labelAt[1] - 18)}
            text={cls?.name ?? `#${ann.category_id}`}
            fontSize={11}
            fontFamily="Inter, sans-serif"
            fontStyle="600"
            fill={color}
            shadowColor="#000"
            shadowBlur={2}
            listening={false}
          />
        )}
      </Group>
    );
  };

  return (
    <Group>
      {frame?.annotations.map((ann) =>
        renderInstance(`a${ann.id}`, ann, { selected: ann.id === selectedAnnotationId, wip: false })
      )}
      {kpWip &&
        renderInstance(
          "wip",
          { category_id: kpWip.categoryId, keypoints: kpWip.points },
          { selected: false, wip: true }
        )}
    </Group>
  );
}

/** Instância de keypoint sob o ponteiro: ponto mais próximo dentro de `radius` (px da imagem). */
export function keypointAt(
  annotations: Annotation[],
  x: number,
  y: number,
  radius: number
): { annId: number; index: number } | null {
  let best: { annId: number; index: number } | null = null;
  let bestDist = radius;
  for (const ann of annotations) {
    (ann.keypoints ?? []).forEach((p, index) => {
      if (p[2] <= 0) return;
      const dist = Math.hypot(p[0] - x, p[1] - y);
      if (dist <= bestDist) {
        bestDist = dist;
        best = { annId: ann.id, index };
      }
    });
  }
  return best;
}
