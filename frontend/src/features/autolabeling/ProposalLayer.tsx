import { Rect } from "react-konva";
import { useSessionStore } from "../../shared/session/store";
import { useAnnotationStore } from "../annotate/store";
import type { ImageFit } from "../annotate/canvas/useImageFit";
import { useAutolabelingStore } from "./store";

export default function ProposalLayer({ fit }: { fit: ImageFit }) {
  const { proposals, drafts, visible, selectedId, sessionId, edit } = useAutolabelingStore();
  const activeSessionId = useSessionStore((s) => s.sessionId);
  const frame = useAnnotationStore((s) => s.frame);
  const tool = useAnnotationStore((s) => s.tool);
  if (!visible || sessionId !== activeSessionId) return null;
  return <>{proposals.filter((p) => p.frame_index === frame?.index && p.status === "pending").map((p) => {
    const [x, y, w, h] = drafts[p.id]?.bbox ?? p.bbox;
    const selected = selectedId === p.id;
    return <Rect key={p.id} x={fit.offsetX + x * fit.scale} y={fit.offsetY + y * fit.scale}
      width={w * fit.scale} height={h * fit.scale} stroke="#f59e0b" strokeWidth={selected ? 3 : 2}
      dash={[7, 4]} fill={selected ? "rgba(245,158,11,0.12)" : undefined}
      draggable={selected && tool === "select"}
      onMouseDown={(e) => { e.cancelBubble = true; useAutolabelingStore.setState({ selectedId: p.id }); }}
      onMouseUp={(e) => { e.cancelBubble = true; }}
      onDragEnd={(e) => {
        e.cancelBubble = true;
        const left = Math.max(0, Math.min((e.target.x() - fit.offsetX) / fit.scale, fit.imgW - w));
        const top = Math.max(0, Math.min((e.target.y() - fit.offsetY) / fit.scale, fit.imgH - h));
        e.target.position({ x: fit.offsetX + left * fit.scale, y: fit.offsetY + top * fit.scale });
        edit(p, { bbox: [left, top, w, h] });
      }} />;
  })}</>;
}
