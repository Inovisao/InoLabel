import { useEffect, useRef, useState, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect } from "react-konva";
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
  const { frame, classes, selectedClassId, addAnnotation, removeAnnotation } =
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

  const toImageCoords = useCallback(
    (stageX: number, stageY: number) => ({
      x: (stageX - offsetX) / imgScale,
      y: (stageY - offsetY) / imgScale,
    }),
    [offsetX, offsetY, imgScale]
  );

  const handleMouseDown = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (e.evt.button !== 0) return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    setStartPos({ x: pos.x, y: pos.y });
    setDrawing({ x: pos.x, y: pos.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    if (!startPos) return;
    const pos = e.target.getStage()?.getPointerPosition();
    if (!pos) return;
    setDrawing({
      x: Math.min(pos.x, startPos.x),
      y: Math.min(pos.y, startPos.y),
      w: Math.abs(pos.x - startPos.x),
      h: Math.abs(pos.y - startPos.y),
    });
  };

  const handleMouseUp = async () => {
    if (!drawing || !startPos || drawing.w < 5 || drawing.h < 5) {
      setDrawing(null);
      setStartPos(null);
      return;
    }
    const tl = toImageCoords(drawing.x, drawing.y);
    await addAnnotation([tl.x, tl.y, drawing.w / imgScale, drawing.h / imgScale]);
    setDrawing(null);
    setStartPos(null);
  };

  const selectedClass = classes.find((c) => c.id === selectedClassId);
  const color = selectedClass?.color ?? "#4F46E5";

  return (
    <>
      <div
        ref={containerRef}
        style={{
          flex: 1,
          background: "var(--color-canvas-bg)",
          overflow: "hidden",
          position: "relative",
          cursor: "crosshair",
        }}
      >
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

            {frame?.annotations.map((ann) => {
              const cls = classes.find((c) => c.id === ann.category_id);
              const clsColor = cls?.color ?? "#4F46E5";
              const [bx, by, bw, bh] = ann.bbox;
              return (
                <Rect
                  key={ann.id}
                  x={offsetX + bx * imgScale}
                  y={offsetY + by * imgScale}
                  width={bw * imgScale}
                  height={bh * imgScale}
                  stroke={clsColor}
                  strokeWidth={2}
                  listening={true}
                  onDblClick={() => setConfirmAnnId(ann.id)}
                />
              );
            })}

            {drawing && drawing.w > 2 && drawing.h > 2 && (
              <Rect
                x={drawing.x}
                y={drawing.y}
                width={drawing.w}
                height={drawing.h}
                stroke={color}
                strokeWidth={2}
                dash={[5, 4]}
                listening={false}
              />
            )}
          </Layer>
        </Stage>

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

        {/* Class indicator overlay */}
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
