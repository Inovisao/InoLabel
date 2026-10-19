import { useEffect, useMemo, useRef, useState } from "react";
import type Konva from "konva";
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
import { boundsOf, fadedLabelIds, labelFontSize, labelRect, type Rect as ScreenRect } from "./labelOverlap";
import { obbCorners } from "./obbGeometry";
import ObbShape from "./ObbShape";
import { DEFAULT_DRAW_COLOR, shapeStyle } from "./shapeStyle";
import { activeBinds, useKeybindStore } from "../../keybinds/store";
import { localPointer, useCanvasPointer } from "./useCanvasPointer";
import { useCanvasViewport } from "./useCanvasViewport";
import { toScreen, useImageFit } from "./useImageFit";
import { layerTransform } from "./viewRotation";
import type { View } from "./viewport";

/** A partir daqui (px de tela por px da imagem) os pixels aparecem nítidos, sem suavizar. */
const PIXELATED_FROM_SCALE = 4;

/** Área de anotação: imagem do frame, formas do modo atual e avisos por cima. */
export default function AnnotationCanvas() {
  const store = useAnnotationStore();
  const { frame, classes, selectedClassId, selectedAnnotationId, tool, error, viewRotation } = store;
  const mode = useSessionStore((s) => s.mode);
  const [confirmAnnId, setConfirmAnnId] = useState<number | null>(null);
  const [view, setView] = useState<View | null>(null);
  const binds = useKeybindStore((s) => activeBinds(s.data));

  const imageFit = useImageFit(frame?.image_b64, view, viewRotation);
  const { containerRef, size, img, fit, base, toImageCoords, isInsideImage, ready: imageReady } = imageFit;
  // Tamanho real da imagem do frame atual (colar, mover e girar usam). Só com a imagem
  // do frame já carregada; frames com a mesma imagem (vídeo parado) também atualizam.
  useEffect(() => {
    if (imageReady && img && frame) store.setImageSize({ width: img.width, height: img.height, frameIndex: frame.index });
  }, [imageReady, img, frame?.index]); // eslint-disable-line react-hooks/exhaustive-deps
  // Trocar de frame ou girar a exibição volta ao ajuste.
  const viewport = useCanvasViewport({
    containerRef, base, binds, view, setView, rotation: viewRotation, resetKey: `${frame?.index}:${viewRotation}`,
  });
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
    onToggleSelect: store.toggleInSelection,
    onSelectMany: (ids, additive) =>
      store.selectMany(additive ? [...store.selectedIds, ...ids.filter((id) => !store.selectedIds.includes(id))] : ids),
    onPlacePoint: store.kpPlacePoint,
    onSelectPoint: store.selectKeypoint,
  });

  // Etiquetas transparentes sob o ponteiro: a geometria de cada forma (contorno e etiqueta)
  // na tela, onde a etiqueta é desenhada em pé, e no movimento do mouse só muda o estado
  // quando o conjunto muda.
  const shapeGeometry = useMemo(() => {
    if (!frame || mode === "classification" || mode === "keypoint") return [];
    return frame.annotations.map((ann) => {
      const { label } = shapeStyle(ann, classes.find((c) => c.id === ann.category_id), mode);
      const onScreen = ([x, y]: [number, number]): [number, number] => {
        const p = toScreen(fit, { x: fit.offsetX + x * fit.scale, y: fit.offsetY + y * fit.scale });
        return [p.x, p.y];
      };
      const [bx, by, bw, bh] = ann.bbox;
      const corners: [number, number][] =
        mode === "obb" && ann.obb ? obbCorners(ann.obb) : [[bx, by], [bx + bw, by], [bx + bw, by + bh], [bx, by + bh]];
      const bounds: ScreenRect = boundsOf(corners.map(onScreen));
      return { id: ann.id, bounds, rect: labelRect(bounds.x, bounds.y, label, labelFontSize(bw * fit.scale)) };
    });
  }, [frame, classes, mode, fit]);
  const geometryRef = useRef(shapeGeometry);
  geometryRef.current = shapeGeometry;
  const [fadedKey, setFadedKey] = useState("");
  const fadedIds = useMemo(() => new Set(fadedKey ? fadedKey.split(",").map(Number) : []), [fadedKey]);

  const updateFadedLabels = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const pos = e.target.getStage()?.getPointerPosition() ?? null;
    const local = localPointer(e);
    const hoveredId = local ? pointer.annotationAt(local.x, local.y)?.id : undefined;
    const hovered = geometryRef.current.find((g) => g.id === hoveredId) ?? null;
    setFadedKey(fadedLabelIds(geometryRef.current, pos, hovered).join(","));
  };

  const selectedClass = classes.find((c) => c.id === selectedClassId);
  const drawColor = selectedClass?.color ?? DEFAULT_DRAW_COLOR;
  const showsShapes = mode !== "classification" && mode !== "keypoint";

  // Bloco selecionado sendo arrastado: as outras formas seguem com o mesmo deslocamento
  // (px de tela) até o backend gravar. `draggedId` null = todas deslocadas (gravando).
  const [groupDrag, setGroupDrag] = useState<{ draggedId: number | null; dx: number; dy: number } | null>(null);
  const isGroup = store.selectedIds.length > 1;

  const renderShape = (ann: Annotation) => {
    const { color, label } = shapeStyle(ann, classes.find((c) => c.id === ann.category_id), mode);
    const selected = store.selectedIds.includes(ann.id);
    const inGroup = isGroup && selected;
    const common = {
      fit,
      color,
      label,
      selected,
      movable: selected && tool === "select",
      onRequestRemove: () => setConfirmAnnId(ann.id),
      labelFaded: fadedIds.has(ann.id),
      groupOffset: inGroup && groupDrag && groupDrag.draggedId !== ann.id ? groupDrag : undefined,
      onGroupDragMove: inGroup ? (dx: number, dy: number) => setGroupDrag({ draggedId: ann.id, dx, dy }) : undefined,
      onGroupDragEnd: inGroup
        ? async (dx: number, dy: number) => {
            setGroupDrag({ draggedId: null, dx, dy });
            await store.moveSelection(dx / fit.scale, dy / fit.scale);
            setGroupDrag(null);
          }
        : undefined,
    };
    if (mode === "obb" && ann.obb) {
      return (
        <ObbShape
          key={ann.id}
          ann={ann as Annotation & { obb: OBBGeometry }}
          {...common}
          onChange={(obb) => store.updateAnnotation(ann.id, { obb })}
          onRotateTo={(angle) => store.rotateSelected({ angle })}
          rotatable={ann.id === selectedAnnotationId}
        />
      );
    }
    return (
      <BoxShape
        key={ann.id}
        ann={ann}
        {...common}
        // Redimensionar: só com uma caixa selecionada (no bloco, arrastar move todas).
        resizable={selected && tool === "select" && !isGroup && !groupDrag}
        onMove={(bbox) => store.updateAnnotation(ann.id, { bbox })}
      />
    );
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
          cursor: viewport.panning
            ? "grabbing"
            : viewport.panReady && img
              ? "grab"
              : img && mode !== "classification" && tool === "box"
                ? "crosshair"
                : "default",
        }}
      >
        {error && <ErrorToast error={error} onClose={store.clearError} />}

        <Stage
          width={size.width}
          height={size.height}
          onMouseDown={pointer.onMouseDown}
          onMouseMove={(e) => {
            pointer.onMouseMove(e);
            updateFadedLabels(e);
          }}
          onMouseLeave={() => setFadedKey("")}
          onMouseUp={pointer.onMouseUp}
        >
          <Layer
            imageSmoothingEnabled={fit.scale < PIXELATED_FROM_SCALE}
            {...layerTransform(size.width, size.height, viewRotation)}
          >
            {img && <KonvaImage image={img} x={fit.offsetX} y={fit.offsetY} width={fit.shownW} height={fit.shownH} />}
            {mode === "keypoint" && img && (
              <KeypointLayer offsetX={fit.offsetX} offsetY={fit.offsetY} scale={fit.scale} imgW={fit.imgW} imgH={fit.imgH} fit={fit} />
            )}
            {showsShapes && frame?.annotations.map(renderShape)}
            {pointer.marquee && pointer.marquee.w > 2 && pointer.marquee.h > 2 && (
              <Rect
                x={pointer.marquee.x}
                y={pointer.marquee.y}
                width={pointer.marquee.w}
                height={pointer.marquee.h}
                stroke="#3B82F6"
                strokeWidth={1}
                fill="rgba(59, 130, 246, 0.08)"
                dash={[4, 3]}
                listening={false}
              />
            )}
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
