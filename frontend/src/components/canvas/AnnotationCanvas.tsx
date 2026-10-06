import { useEffect, useRef, useState, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Text, Group, Line, Circle } from "react-konva";
import Konva from "konva";
import { useAnnotationStore } from "../../stores/annotation";
import { useSessionStore } from "../../stores/session";
import type { Annotation, OBBGeometry } from "../../api/types";
import ConfirmModal from "../modals/ConfirmModal";
import KeypointLayer, { keypointAt } from "./KeypointLayer";
import {
  angleFromCenter,
  fitInsideImage,
  obbCorners,
  pointInPolygon,
  rotateTo,
} from "./obbGeometry";

/** Distância (px de tela) da alça de rotação até o lado superior da caixa. */
const ROTATE_HANDLE_OFFSET = 28;
const ROTATE_SNAP_DEG = 15;

interface DrawingRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

const TRACK_COLOR_VARS = [
  "--color-icon-track-fg",
  "--color-icon-detect-fg",
  "--color-icon-obb-fg",
  "--color-icon-class-fg",
  "--color-primary",
  "--color-danger",
];

function colorForTrack(trackId: number) {
  return `var(${TRACK_COLOR_VARS[Math.abs(trackId) % TRACK_COLOR_VARS.length]})`;
}

export default function AnnotationCanvas() {
  const {
    frame,
    classes,
    selectedClassId,
    classificationResult,
    addAnnotation,
    removeAnnotation,
    updateAnnotation,
    selectedAnnotationId,
    selectAnnotation,
    rotateSelected,
    setImageSize,
    kpWip,
    kpNextVisibility,
    kpPlacePoint,
    selectKeypoint,
    tool,
    error,
    clearError,
  } = useAnnotationStore();
  const mode = useSessionStore((s) => s.mode);

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [drawing, setDrawing] = useState<DrawingRect | null>(null);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  const [confirmAnnId, setConfirmAnnId] = useState<number | null>(null);
  /** OBB: geometria em pré-visualização enquanto a alça de rotação é arrastada. */
  const [rotatePreview, setRotatePreview] = useState<OBBGeometry | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() =>
      setSize({ width: el.clientWidth, height: el.clientHeight })
    );
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!frame?.image_b64) { setImg(null); return; }
    const image = new window.Image();
    image.src = `data:image/jpeg;base64,${frame.image_b64}`;
    image.onload = () => {
      setImg(image);
      setImageSize({ width: image.width, height: image.height });
    };
  }, [frame?.image_b64]);

  const imgScale = img ? Math.min(size.width / img.width, size.height / img.height) : 1;
  const imgW = img ? img.width * imgScale : 0;
  const imgH = img ? img.height * imgScale : 0;
  const offsetX = (size.width - imgW) / 2;
  const offsetY = (size.height - imgH) / 2;

  /** Convert stage → image pixel coords, clamped to image bounds */
  const toImageCoords = useCallback(
    (stageX: number, stageY: number) => ({
      x: Math.max(0, Math.min((stageX - offsetX) / imgScale, img?.width ?? 0)),
      y: Math.max(0, Math.min((stageY - offsetY) / imgScale, img?.height ?? 0)),
    }),
    [offsetX, offsetY, imgScale, img]
  );

  /** Caixa sob o ponteiro (a menor, para caixas sobrepostas). */
  const annotationAt = (stageX: number, stageY: number): Annotation | null => {
    if (!frame) return null;
    const { x, y } = toImageCoords(stageX, stageY);
    let best: Annotation | null = null;
    let bestArea = Infinity;
    for (const ann of frame.annotations) {
      // No OBB o teste é pelo polígono girado, não pelo retângulo envolvente.
      const obb = mode === "obb" ? ann.obb : null;
      const [bx, by, bw, bh] = ann.bbox;
      const hit = obb
        ? pointInPolygon(x, y, obbCorners(obb))
        : x >= bx && x <= bx + bw && y >= by && y <= by + bh;
      const area = obb ? obb.width * obb.height : bw * bh;
      if (hit && area < bestArea) {
        best = ann;
        bestArea = area;
      }
    }
    return best;
  };

  const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button !== 0 || !img || mode === "classification") return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    // Alça de rotação ou caixa arrastável: o gesto é delas, não desenha nem seleciona.
    if (e.target.draggable() || e.target.getParent()?.draggable()) return;
    if (mode === "keypoint") {
      const inside =
        pos.x >= offsetX && pos.x <= offsetX + imgW && pos.y >= offsetY && pos.y <= offsetY + imgH;
      if (!inside) return;
      const { x, y } = toImageCoords(pos.x, pos.y);
      if (tool === "box") {
        kpPlacePoint(x, y);   // B: cada clique marca o próximo ponto da classe
      } else {
        // V: clique perto de um ponto seleciona instância + ponto; senão, pela bbox.
        const hit = frame ? keypointAt(frame.annotations, x, y, 10 / imgScale) : null;
        if (hit) selectKeypoint(hit.annId, hit.index);
        else selectAnnotation(annotationAt(pos.x, pos.y)?.id ?? null);
      }
      return;
    }
    // Ferramenta de seleção: clique escolhe a caixa; arrastar move (draggable).
    if (tool === "select") {
      selectAnnotation(annotationAt(pos.x, pos.y)?.id ?? null);
      return;
    }
    // Only start drawing if click is within image bounds
    if (
      pos.x < offsetX || pos.x > offsetX + imgW ||
      pos.y < offsetY || pos.y > offsetY + imgH
    ) return;
    setStartPos({ x: pos.x, y: pos.y });
    setDrawing({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!startPos || !img || mode === "classification") return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    // Clamp to image bounds on screen
    const cx = Math.max(offsetX, Math.min(pos.x, offsetX + imgW));
    const cy = Math.max(offsetY, Math.min(pos.y, offsetY + imgH));
    setDrawing({
      x: Math.min(cx, startPos.x),
      y: Math.min(cy, startPos.y),
      w: Math.abs(cx - startPos.x),
      h: Math.abs(cy - startPos.y),
    });
  };

  const handleMouseUp = async () => {
    if (mode === "classification") {
      setDrawing(null);
      setStartPos(null);
      return;
    }
    if (!drawing || !startPos || drawing.w < 5 || drawing.h < 5) {
      // Clique sem arrastar também seleciona a caixa sob o ponteiro.
      if (startPos) selectAnnotation(annotationAt(startPos.x, startPos.y)?.id ?? null);
      setDrawing(null);
      setStartPos(null);
      return;
    }
    const tl = toImageCoords(drawing.x, drawing.y);
    const br = toImageCoords(drawing.x + drawing.w, drawing.y + drawing.h);
    const bboxW = Math.max(1, br.x - tl.x);
    const bboxH = Math.max(1, br.y - tl.y);
    await addAnnotation([tl.x, tl.y, bboxW, bboxH]);
    setDrawing(null);
    setStartPos(null);
  };

  const selectedClass = classes.find((c) => c.id === selectedClassId);
  const drawColor = selectedClass?.color ?? "#4F46E5";

  return (
    <>
      <div
        ref={containerRef}
        style={{
          flex: 1,
          background: "var(--color-canvas-bg)",
          overflow: "hidden",
          position: "relative",
          cursor: img && mode !== "classification" && tool === "box" ? "crosshair" : "default",
        }}
      >
        {/* Error toast */}
        {error && (
          <div
            onClick={clearError}
            style={{
              position: "absolute",
              top: 12,
              left: "50%",
              transform: "translateX(-50%)",
              zIndex: 10,
              padding: "8px 16px",
              background: "var(--overlay-canvas-error)",
              color: "var(--color-text-inverse)",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
              backdropFilter: "blur(4px)",
              maxWidth: 400,
              textAlign: "center",
            }}
          >
            {error} · clique para fechar
          </div>
        )}

        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        >
          <Layer>
            {img && (
              <KonvaImage
                image={img}
                x={offsetX}
                y={offsetY}
                width={imgW}
                height={imgH}
              />
            )}

            {/* Existing annotations */}
            {mode === "keypoint" && img && (
              <KeypointLayer offsetX={offsetX} offsetY={offsetY} scale={imgScale} imgW={img.width} imgH={img.height} />
            )}

            {mode !== "classification" && mode !== "keypoint" && frame?.annotations.map((ann) => {
              const cls = classes.find((c) => c.id === ann.category_id);
              const hasTrack = mode === "tracking" && ann.track_id != null;
              const clsColor = hasTrack
                ? colorForTrack(ann.track_id as number)
                : cls?.color ?? "#4F46E5";
              const clsName = cls?.name ?? `#${ann.category_id}`;
              const label = hasTrack
                ? `ID ${ann.track_id} | ${clsName}`
                : mode === "tracking"
                  ? `sem ID | ${clsName}`
                  : clsName;
              const selected = ann.id === selectedAnnotationId;
              const strokeWidth = selected ? 3 : 2;
              const [bx, by, bw, bh] = ann.bbox;
              const sx = offsetX + bx * imgScale;
              const sy = offsetY + by * imgScale;
              const sw = bw * imgScale;
              const sh = bh * imgScale;
              const labelFontSize = Math.max(10, Math.min(14, sw * 0.12));
              const geometry = mode === "obb" && ann.obb
                ? (selected && rotatePreview) || ann.obb
                : null;
              const points = geometry ? obbCorners(geometry) : null;

              if (geometry && points) {
                const scaled = points.flatMap(([px, py]) => [
                  offsetX + px * imgScale,
                  offsetY + py * imgScale,
                ]);
                const labelX = Math.min(...points.map(([px]) => offsetX + px * imgScale));
                const labelY = Math.min(...points.map(([, py]) => offsetY + py * imgScale));

                // Alça: acima do meio do lado superior, na direção "para cima" da caixa.
                const upAngle = ((geometry.angle - 90) * Math.PI) / 180;
                const topMidX = offsetX + ((points[0][0] + points[1][0]) / 2) * imgScale;
                const topMidY = offsetY + ((points[0][1] + points[1][1]) / 2) * imgScale;
                const handleX = topMidX + Math.cos(upAngle) * ROTATE_HANDLE_OFFSET;
                const handleY = topMidY + Math.sin(upAngle) * ROTATE_HANDLE_OFFSET;
                const centerX = offsetX + geometry.cx * imgScale;
                const centerY = offsetY + geometry.cy * imgScale;

                return (
                  <Group
                    key={ann.id}
                    onDblClick={() => setConfirmAnnId(ann.id)}
                    draggable={selected && tool === "select"}
                    onDragEnd={(e) => {
                      if (e.target !== e.currentTarget || !img) return;
                      const dx = e.target.x() / imgScale;
                      const dy = e.target.y() / imgScale;
                      e.target.position({ x: 0, y: 0 });
                      const moved = fitInsideImage(
                        { ...ann.obb!, cx: ann.obb!.cx + dx, cy: ann.obb!.cy + dy },
                        img.width,
                        img.height
                      );
                      if (moved) updateAnnotation(ann.id, { obb: moved });
                    }}
                  >
                    <Line
                      points={scaled}
                      closed
                      stroke={clsColor}
                      strokeWidth={strokeWidth}
                      dash={selected ? [8, 4] : undefined}
                      fill="transparent"
                      listening={true}
                    />
                    <Rect
                      x={labelX}
                      y={Math.max(0, labelY - labelFontSize - 4)}
                      width={label.length * labelFontSize * 0.6 + 8}
                      height={labelFontSize + 4}
                      fill={clsColor}
                      cornerRadius={3}
                      listening={false}
                    />
                    <Text
                      x={labelX + 4}
                      y={Math.max(2, labelY - labelFontSize - 1)}
                      text={label}
                      fontSize={labelFontSize}
                      fontFamily="Inter, sans-serif"
                      fontStyle="600"
                      fill="#fff"
                      listening={false}
                    />
                    {selected && (
                      <>
                        <Line
                          points={[topMidX, topMidY, handleX, handleY]}
                          stroke={clsColor}
                          strokeWidth={1.5}
                          listening={false}
                        />
                        <Circle
                          x={handleX}
                          y={handleY}
                          radius={7}
                          fill="#fff"
                          stroke={clsColor}
                          strokeWidth={2}
                          draggable
                          onMouseEnter={(e) => {
                            const c = e.target.getStage()?.container();
                            if (c) c.style.cursor = "grab";
                          }}
                          onMouseLeave={(e) => {
                            const c = e.target.getStage()?.container();
                            if (c) c.style.cursor = "";
                          }}
                          onDragMove={(e) => {
                            if (!img || !ann.obb) return;
                            const pos = e.target.getStage()?.getPointerPosition();
                            if (!pos) return;
                            // +90: a alça fica no "para cima" da caixa (ângulo − 90°).
                            let angle = angleFromCenter(centerX, centerY, pos.x, pos.y) + 90;
                            if (e.evt.shiftKey) angle = Math.round(angle / ROTATE_SNAP_DEG) * ROTATE_SNAP_DEG;
                            const next = rotateTo(ann.obb, angle, img.width, img.height);
                            if (next) setRotatePreview(next);
                            // Mantém a alça sobre o arco, não onde o ponteiro largou.
                            e.target.position({ x: handleX, y: handleY });
                          }}
                          onDragEnd={async (e) => {
                            e.cancelBubble = true;
                            const preview = rotatePreview;
                            if (preview) await rotateSelected({ angle: preview.angle });
                            setRotatePreview(null);
                          }}
                        />
                      </>
                    )}
                  </Group>
                );
              }

              return (
                <Group key={ann.id} onDblClick={() => setConfirmAnnId(ann.id)}>
                  {/* Bbox rectangle */}
                  <Rect
                    x={sx}
                    y={sy}
                    width={sw}
                    height={sh}
                    stroke={clsColor}
                    strokeWidth={strokeWidth}
                    dash={selected ? [8, 4] : undefined}
                    fill="transparent"
                    listening={true}
                    draggable={selected && tool === "select"}
                    dragBoundFunc={(p) => ({
                      x: Math.max(offsetX, Math.min(p.x, offsetX + imgW - sw)),
                      y: Math.max(offsetY, Math.min(p.y, offsetY + imgH - sh)),
                    })}
                    onDragEnd={(e) => {
                      const nx = (e.target.x() - offsetX) / imgScale;
                      const ny = (e.target.y() - offsetY) / imgScale;
                      updateAnnotation(ann.id, { bbox: [nx, ny, bw, bh] });
                    }}
                  />
                  {/* Label background */}
                  <Rect
                    x={sx}
                    y={Math.max(0, sy - labelFontSize - 4)}
                    width={label.length * labelFontSize * 0.6 + 8}
                    height={labelFontSize + 4}
                    fill={clsColor}
                    cornerRadius={3}
                    listening={false}
                  />
                  {/* Label text */}
                  <Text
                    x={sx + 4}
                    y={Math.max(2, sy - labelFontSize - 1)}
                    text={label}
                    fontSize={labelFontSize}
                    fontFamily="Inter, sans-serif"
                    fontStyle="600"
                    fill="#fff"
                    listening={false}
                  />
                </Group>
              );
            })}

            {/* Drawing preview */}
            {drawing && drawing.w > 2 && drawing.h > 2 && (
              <Rect
                x={drawing.x}
                y={drawing.y}
                width={drawing.w}
                height={drawing.h}
                stroke={drawColor}
                strokeWidth={2}
                fill={`${drawColor}18`}
                dash={[6, 4]}
                listening={false}
              />
            )}
          </Layer>
        </Stage>

        {/* Empty state */}
        {!frame && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-canvas-muted)",
              fontSize: 14,
              gap: 8,
              pointerEvents: "none",
            }}
          >
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.4">
              <rect x="8" y="8" width="32" height="32" rx="4" stroke="var(--color-text-inverse)" strokeWidth="1.5" />
              <circle cx="18" cy="20" r="3" stroke="var(--color-text-inverse)" strokeWidth="1.5" />
              <path d="M8 34l9-9 5 5 7-8 11 12" stroke="var(--color-text-inverse)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span>Carregando frame…</span>
          </div>
        )}

        {/* Active class indicator */}
        {frame && selectedClass && (
          <div
            style={{
              position: "absolute",
              bottom: 12,
              right: 12,
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 10px",
              background: "var(--overlay-canvas-control)",
              backdropFilter: "blur(4px)",
              borderRadius: 999,
              pointerEvents: "none",
            }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: selectedClass.color ?? "#4F46E5",
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: 12, color: "var(--color-text-inverse)", fontWeight: 500 }}>
              {selectedClass.name}
            </span>
          </div>
        )}

        {/* Keypoint: qual é o próximo ponto */}
        {mode === "keypoint" && frame && tool === "box" && (() => {
          const cls = classes.find((c) => c.id === (kpWip?.categoryId ?? selectedClassId));
          const names = cls?.keypoints ?? [];
          if (!names.length) return null;
          const index = kpWip?.index ?? 0;
          return (
            <div
              style={{
                position: "absolute",
                top: 12,
                left: "50%",
                transform: "translateX(-50%)",
                padding: "6px 12px",
                background: "var(--overlay-canvas-control)",
                color: "var(--color-text-inverse)",
                borderRadius: "var(--radius-md)",
                fontSize: 12,
                pointerEvents: "none",
                whiteSpace: "nowrap",
              }}
            >
              {cls?.name} · próximo: <strong>{names[index]}</strong> ({index + 1}/{names.length})
              {" · "}
              {kpNextVisibility === 2 ? "visível" : "oculto"}
            </div>
          );
        })()}

        {/* Hint */}
        {frame && (
          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              fontSize: 11,
              color: "var(--color-canvas-subtle)",
              pointerEvents: "none",
            }}
          >
            {mode === "classification"
              ? "Clique na classe ou digite o número dela · Espaço pula · Ctrl+Z desfaz"
              : mode === "keypoint"
                ? tool === "select"
                  ? "Clique num ponto para selecionar · arraste para mover · C visível/oculto · Del apaga a instância · B volta a marcar"
                  : "Clique para marcar os pontos em ordem · X pula o ponto · C visível/oculto · F fecha · Backspace desfaz o ponto · Esc cancela"
              : mode === "obb" && selectedAnnotationId !== null
                ? "Arraste a alça ○ para girar (Shift: 15°) · Q / E giram 5° · V e arraste para mover · Del remove"
                : tool === "select"
                ? "Clique para selecionar · arraste a caixa selecionada para mover · Del remove · B volta a desenhar"
                : "Arraste para anotar · clique numa caixa para editar · N marca frame sem objetos · Ctrl+Z desfaz"}
          </div>
        )}

        {mode === "classification" && frame?.classification_id != null && (
          <div
            style={{
              position: "absolute",
              top: 12,
              right: 12,
              padding: "8px 12px",
              background: "var(--overlay-canvas-control)",
              color: "var(--color-text-inverse)",
              borderRadius: "var(--radius-md)",
              fontSize: 12,
              fontWeight: 600,
              pointerEvents: "none",
            }}
          >
            Classe: {classes.find((c) => c.id === frame.classification_id)?.name ?? classificationResult?.top1_class_name}
          </div>
        )}
      </div>

      <ConfirmModal
        open={confirmAnnId !== null}
        title="Remover anotação"
        description="Tem certeza que deseja remover esta anotação? Esta ação não pode ser desfeita."
        confirmLabel="Remover"
        danger
        onConfirm={async () => {
          if (confirmAnnId !== null) {
            await removeAnnotation(confirmAnnId);
            setConfirmAnnId(null);
          }
        }}
        onCancel={() => setConfirmAnnId(null)}
      />
    </>
  );
}
