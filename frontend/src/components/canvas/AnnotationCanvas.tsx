import { useEffect, useRef, useState, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Text, Group } from "react-konva";
import Konva from "konva";
import { useAnnotationStore } from "../../stores/annotation";
import ConfirmModal from "../modals/ConfirmModal";

interface DrawingRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export default function AnnotationCanvas() {
  const { frame, classes, selectedClassId, addAnnotation, removeAnnotation, error, clearError } =
    useAnnotationStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 800, height: 600 });
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  const [drawing, setDrawing] = useState<DrawingRect | null>(null);
  const [startPos, setStartPos] = useState<{ x: number; y: number } | null>(null);
  const [confirmAnnId, setConfirmAnnId] = useState<number | null>(null);

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
    image.onload = () => setImg(image);
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

  const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button !== 0 || !img) return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    // Only start drawing if click is within image bounds
    if (
      pos.x < offsetX || pos.x > offsetX + imgW ||
      pos.y < offsetY || pos.y > offsetY + imgH
    ) return;
    setStartPos({ x: pos.x, y: pos.y });
    setDrawing({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!startPos || !img) return;
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
    if (!drawing || !startPos || drawing.w < 5 || drawing.h < 5) {
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
          cursor: img ? "crosshair" : "default",
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
              background: "rgba(220,38,38,0.9)",
              color: "#fff",
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
            {frame?.annotations.map((ann) => {
              const cls = classes.find((c) => c.id === ann.category_id);
              const clsColor = cls?.color ?? "#4F46E5";
              const clsName = cls?.name ?? `#${ann.category_id}`;
              const [bx, by, bw, bh] = ann.bbox;
              const sx = offsetX + bx * imgScale;
              const sy = offsetY + by * imgScale;
              const sw = bw * imgScale;
              const sh = bh * imgScale;
              const labelFontSize = Math.max(10, Math.min(14, sw * 0.12));

              return (
                <Group key={ann.id} onDblClick={() => setConfirmAnnId(ann.id)}>
                  {/* Bbox rectangle */}
                  <Rect
                    x={sx}
                    y={sy}
                    width={sw}
                    height={sh}
                    stroke={clsColor}
                    strokeWidth={2}
                    fill={`${clsColor}18`}
                    listening={true}
                  />
                  {/* Label background */}
                  <Rect
                    x={sx}
                    y={Math.max(0, sy - labelFontSize - 4)}
                    width={clsName.length * labelFontSize * 0.6 + 8}
                    height={labelFontSize + 4}
                    fill={clsColor}
                    cornerRadius={3}
                    listening={false}
                  />
                  {/* Label text */}
                  <Text
                    x={sx + 4}
                    y={Math.max(2, sy - labelFontSize - 1)}
                    text={clsName}
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
              color: "rgba(255,255,255,0.3)",
              fontSize: 14,
              gap: 8,
              pointerEvents: "none",
            }}
          >
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.4">
              <rect x="8" y="8" width="32" height="32" rx="4" stroke="white" strokeWidth="1.5" />
              <circle cx="18" cy="20" r="3" stroke="white" strokeWidth="1.5" />
              <path d="M8 34l9-9 5 5 7-8 11 12" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
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
              background: "rgba(0,0,0,0.55)",
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
            <span style={{ fontSize: 12, color: "#fff", fontWeight: 500 }}>
              {selectedClass.name}
            </span>
          </div>
        )}

        {/* Hint */}
        {frame && (
          <div
            style={{
              position: "absolute",
              bottom: 12,
              left: 12,
              fontSize: 11,
              color: "rgba(255,255,255,0.4)",
              pointerEvents: "none",
            }}
          >
            Arraste para anotar · Duplo clique na caixa para remover
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
