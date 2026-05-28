import { useRef, useCallback, useState, useEffect } from 'react'
import { useAnnotationStore } from '@/stores/annotationStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/lib/api'
import { BboxOverlay } from './BboxOverlay'
import { ROIOverlay } from './ROIOverlay'

export function AnnotationCanvas() {
  const state = useAnnotationStore(s => s.state)
  const setState = useAnnotationStore(s => s.setState)
  const { canvasMode, setCanvasMode } = useUIStore()

  const containerRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)

  // Drawing state
  const [drawing, setDrawing] = useState(false)
  const [drawStart, setDrawStart] = useState<[number, number] | null>(null)
  const [drawCurrent, setDrawCurrent] = useState<[number, number] | null>(null)

  // Pan state
  const panStartRef = useRef<{ mx: number; my: number; ox: number; oy: number } | null>(null)
  const [panOffset, setPanOffset] = useState<[number, number]>([0, 0])

  // ROI collection state
  const [roiPoints, setRoiPoints] = useState<[number, number][]>([])

  // Displayed image dimensions (actual render size)
  const [imgSize, setImgSize] = useState<{ w: number; h: number; ox: number; oy: number } | null>(null)

  // Update img size on load / container resize
  const updateImgSize = useCallback(() => {
    const img = imgRef.current
    if (!img) return
    const r = img.getBoundingClientRect()
    const cr = containerRef.current?.getBoundingClientRect()
    setImgSize({ w: r.width, h: r.height, ox: r.left - (cr?.left ?? 0), oy: r.top - (cr?.top ?? 0) })
  }, [])

  useEffect(() => {
    const obs = new ResizeObserver(updateImgSize)
    if (containerRef.current) obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [updateImgSize])


  const getRelativePos = (e: React.MouseEvent): [number, number] => {
    const r = containerRef.current!.getBoundingClientRect()
    return [e.clientX - r.left, e.clientY - r.top]
  }

  const act = async (fn: () => Promise<typeof state>) => {
    try { const s = await fn(); if (s) setState(s) } catch { /* ignore */ }
  }

  // ── Mouse handlers ──────────────────────────────────────────────────────

  const onMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return
    const pos = getRelativePos(e)

    if (canvasMode === 'pan') {
      panStartRef.current = { mx: pos[0], my: pos[1], ox: panOffset[0], oy: panOffset[1] }
      return
    }

    if (canvasMode === 'roi') {
      const imgCoords = imgToFrameCoords(pos)
      if (imgCoords) {
        const newPoints = [...roiPoints, imgCoords] as [number, number][]
        setRoiPoints(newPoints)
        if (newPoints.length === 4) {
          act(() => api.frame.setROI(newPoints))
          setRoiPoints([])
          setCanvasMode('validate')
        }
      }
      return
    }

    if (canvasMode === 'draw') {
      setDrawStart(pos)
      setDrawCurrent(pos)
      setDrawing(true)
    }
  }

  const onMouseMove = (e: React.MouseEvent) => {
    const pos = getRelativePos(e)

    if (canvasMode === 'pan' && panStartRef.current) {
      const { mx, my, ox, oy } = panStartRef.current
      setPanOffset([ox + (pos[0] - mx), oy + (pos[1] - my)])
      return
    }

    if (drawing) setDrawCurrent(pos)
  }

  const onMouseUp = (_e: React.MouseEvent) => {
    if (canvasMode === 'pan') { panStartRef.current = null; return }

    if (canvasMode === 'draw' && drawing && drawStart && drawCurrent) {
      const bbox = normalizeBbox(drawStart, drawCurrent)
      if (bbox[2] - bbox[0] > 5 && bbox[3] - bbox[1] > 5) {
        const frameBbox = containerToFrameBbox(bbox)
        const catId = state?.categories?.[0]?.id ?? 1
        act(() => api.frame.addManual(frameBbox, catId))
      }
      setDrawing(false); setDrawStart(null); setDrawCurrent(null)
    }

  }

  const normalizeBbox = (a: [number, number], b: [number, number]): [number, number, number, number] => [
    Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])
  ]

  // Convert container pixel coords to frame image coords (proportional)
  const imgToFrameCoords = (pos: [number, number]): [number, number] | null => {
    if (!imgSize) return null
    const { w, h, ox, oy } = imgSize
    return [(pos[0] - ox) / w, (pos[1] - oy) / h]
  }

  // Convert container bbox to frame-space bbox
  const containerToFrameBbox = (bbox: [number, number, number, number]) => {
    if (!imgSize) return bbox
    const { w, h, ox, oy } = imgSize
    return [
      (bbox[0] - ox) / w, (bbox[1] - oy) / h,
      (bbox[2] - ox) / w, (bbox[3] - oy) / h,
    ]
  }


  const cursor = {
    validate: 'cursor-default',
    draw: 'cursor-crosshair',
    select: 'cursor-pointer',
    remove: 'cursor-pointer',
    pan: panStartRef.current ? 'cursor-grabbing' : 'cursor-grab',
    roi: 'cursor-crosshair',
  }[canvasMode]

  const frameSrc = state?.frame_b64 ? `data:image/jpeg;base64,${state.frame_b64}` : null

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full bg-slate-950 overflow-hidden flex items-center justify-center select-none ${cursor}`}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={() => { if (drawing) { setDrawing(false); setDrawStart(null); setDrawCurrent(null) } }}
    >
      {frameSrc ? (
        <div
          className="relative"
          style={{ transform: `translate(${panOffset[0]}px, ${panOffset[1]}px)` }}
        >
          <img
            ref={imgRef}
            src={frameSrc}
            alt="frame"
            className="max-w-full max-h-full block"
            style={{ maxHeight: 'calc(100vh - 76px)' }}
            onLoad={updateImgSize}
            draggable={false}
          />

          {/* SVG overlays (absolute, same size as image) */}
          {imgSize && (
            <svg
              className="absolute inset-0 pointer-events-none"
              width={imgSize.w} height={imgSize.h}
              viewBox={`0 0 ${imgSize.w} ${imgSize.h}`}
            >
              <BboxOverlay
                detections={[
                  ...(state?.current_detections ?? []).map(d => ({ ...d, source: 'model' as const })),
                  ...(state?.manual_detections ?? []).map(d => ({ ...d, source: 'manual' as const })),
                ]}
                categories={state?.categories ?? []}
                selected={state?.selected_detection}
                imgW={imgSize.w} imgH={imgSize.h}
                frameW={state?.frame_b64 ? 1 : 1}  // normalized coords
              />
              <ROIOverlay
                points={state?.roi_points ?? []}
                pendingPoints={roiPoints}
                imgW={imgSize.w} imgH={imgSize.h}
              />

              {/* Active draw rectangle */}
              {drawing && drawStart && drawCurrent && imgSize && (
                <rect
                  x={Math.min(drawStart[0] - imgSize.ox, drawCurrent[0] - imgSize.ox)}
                  y={Math.min(drawStart[1] - imgSize.oy, drawCurrent[1] - imgSize.oy)}
                  width={Math.abs(drawCurrent[0] - drawStart[0])}
                  height={Math.abs(drawCurrent[1] - drawStart[1])}
                  fill="none" stroke="#facc15" strokeWidth={2} strokeDasharray="5,3"
                />
              )}
            </svg>
          )}
        </div>
      ) : (
        <div className="text-slate-600 text-sm flex flex-col items-center gap-3">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center">
            <span className="text-3xl">🎬</span>
          </div>
          <p>Aguardando sessão...</p>
        </div>
      )}
    </div>
  )
}
