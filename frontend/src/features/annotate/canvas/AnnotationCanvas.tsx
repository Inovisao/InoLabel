import { useState } from "react";
import { Image as KonvaImage, Layer, Rect, Stage } from "react-konva";
import type { Annotation, OBBGeometry } from "../../../shared/api/types";
import { useSessionStore } from "../../../shared/session/store";
import ConfirmModal from "../../../shared/ui/ConfirmModal";
import { useAnnotationStore } from "../store";
import BoxShape from "./BoxShape";
import {
  ActiveClassBadge,
  CanvasHint,
  ClassificationBadge,
  ErrorToast,
  LoadingFrame,
  NextKeypointBanner,
} from "./CanvasOverlays";
import KeypointLayer from "./KeypointLayer";
import ObbShape from "./ObbShape";
import { DEFAULT_DRAW_COLOR, shapeStyle } from "./shapeStyle";
import { useCanvasPointer } from "./useCanvasPointer";
import { useImageFit } from "./useImageFit";

/** Área de anotação: imagem do frame, formas do modo atual e avisos por cima. */
export default function AnnotationCanvas() {
  const store = useAnnotationStore();
  const { frame, classes, selectedClassId, selectedAnnotationId, tool, error } = store;
  const mode = useSessionStore((s) => s.mode);
  const [confirmAnnId, setConfirmAnnId] = useState<number | null>(null);

  const { containerRef, size, img, fit, toImageCoords, isInsideImage } = useImageFit(
    frame?.image_b64,
    store.setImageSize
  );
  const pointer = useCanvasPointer({
    mode,
    tool,
    annotations: frame?.annotations ?? [],
    hasImage: !!img,
    scale: fit.scale,
    toImageCoords,
    isInsideImage,
    clampToImage: (x, y) => ({
      x: Math.max(fit.offsetX, Math.min(x, fit.offsetX + fit.shownW)),
      y: Math.max(fit.offsetY, Math.min(y, fit.offsetY + fit.shownH)),
    }),
    onDrawBox: store.addAnnotation,
    onSelect: store.selectAnnotation,
    onPlacePoint: store.kpPlacePoint,
    onSelectPoint: store.selectKeypoint,
  });

  const selectedClass = classes.find((c) => c.id === selectedClassId);
  const drawColor = selectedClass?.color ?? DEFAULT_DRAW_COLOR;
  const showsShapes = mode !== "classification" && mode !== "keypoint";

  const renderShape = (ann: Annotation) => {
    const { color, label } = shapeStyle(ann, classes.find((c) => c.id === ann.category_id), mode);
    const selected = ann.id === selectedAnnotationId;
    const common = {
      fit,
      color,
      label,
      selected,
      movable: selected && tool === "select",
      onRequestRemove: () => setConfirmAnnId(ann.id),
    };
    if (mode === "obb" && ann.obb) {
      return (
        <ObbShape
          key={ann.id}
          ann={ann as Annotation & { obb: OBBGeometry }}
          {...common}
          onChange={(obb) => store.updateAnnotation(ann.id, { obb })}
          onRotateTo={(angle) => store.rotateSelected({ angle })}
        />
      );
    }
    return <BoxShape key={ann.id} ann={ann} {...common} onMove={(bbox) => store.updateAnnotation(ann.id, { bbox })} />;
  };

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
        {error && <ErrorToast error={error} onClose={store.clearError} />}

        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={pointer.onMouseDown}
          onMouseMove={pointer.onMouseMove}
          onMouseUp={pointer.onMouseUp}
        >
          <Layer>
            {img && <KonvaImage image={img} x={fit.offsetX} y={fit.offsetY} width={fit.shownW} height={fit.shownH} />}
            {mode === "keypoint" && img && (
              <KeypointLayer offsetX={fit.offsetX} offsetY={fit.offsetY} scale={fit.scale} imgW={fit.imgW} imgH={fit.imgH} />
            )}
            {showsShapes && frame?.annotations.map(renderShape)}
            {pointer.drawing && pointer.drawing.w > 2 && pointer.drawing.h > 2 && (
              <Rect
                x={pointer.drawing.x}
                y={pointer.drawing.y}
                width={pointer.drawing.w}
                height={pointer.drawing.h}
                stroke={drawColor}
                strokeWidth={2}
                fill={`${drawColor}18`}
                dash={[6, 4]}
                listening={false}
              />
            )}
          </Layer>
        </Stage>

        {!frame && <LoadingFrame />}
        {frame && selectedClass && <ActiveClassBadge cls={selectedClass} />}
        {mode === "keypoint" && frame && tool === "box" && (
          <NextKeypointBanner
            cls={classes.find((c) => c.id === (store.kpWip?.categoryId ?? selectedClassId))}
            wip={store.kpWip}
            visibility={store.kpNextVisibility}
          />
        )}
        {frame && <CanvasHint mode={mode} tool={tool} hasSelection={selectedAnnotationId !== null} />}
        {mode === "classification" && frame?.classification_id != null && (
          <ClassificationBadge
            name={classes.find((c) => c.id === frame.classification_id)?.name ?? store.classificationResult?.top1_class_name}
          />
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
            await store.removeAnnotation(confirmAnnId);
            setConfirmAnnId(null);
          }
        }}
        onCancel={() => setConfirmAnnId(null)}
      />
    </>
  );
}
