import type { Detection, Category } from '@/lib/types'

const CLASS_COLORS = [
  '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6',
  '#06b6d4','#f97316','#14b8a6','#ec4899','#84cc16',
]

interface Props {
  detections: Detection[]
  categories: Category[]
  selected: [string, number] | null | undefined
  imgW: number
  imgH: number
  frameW: number
}

export function BboxOverlay({ detections, categories, selected, imgW, imgH }: Props) {
  const catMap = new Map(categories.map((c, i) => [c.id, { name: c.name, color: CLASS_COLORS[i % CLASS_COLORS.length] }]))

  return (
    <>
      {detections.map((det, globalIdx) => {
        const [x1, y1, x2, y2] = det.bbox
        const cat = catMap.get(det.category_id)
        const color = cat?.color ?? '#22c55e'
        const isSelected = selected?.[0] === det.source &&
          detections.filter(d => d.source === det.source).indexOf(det) === selected?.[1]
        const thick = isSelected ? 3 : det.source === 'manual' ? 2 : 1.5

        const rx = x1 * imgW, ry = y1 * imgH
        const rw = (x2 - x1) * imgW, rh = (y2 - y1) * imgH

        const label = [
          cat?.name ?? `id:${det.category_id}`,
          det.track_id !== null ? `#${det.track_id}` : '',
          det.source === 'model' ? `${(det.confidence * 100).toFixed(0)}%` : 'manual',
        ].filter(Boolean).join(' ')

        return (
          <g key={`${det.source}-${globalIdx}`}>
            <rect
              x={rx} y={ry} width={rw} height={rh}
              fill="none"
              stroke={isSelected ? '#facc15' : color}
              strokeWidth={thick}
              strokeDasharray={det.source === 'model' ? undefined : '4,2'}
            />
            {/* Label background */}
            <rect
              x={rx} y={Math.max(0, ry - 18)}
              width={label.length * 6.5 + 6} height={16}
              fill={isSelected ? '#facc15' : color}
              fillOpacity={0.85}
              rx={2}
            />
            <text
              x={rx + 3} y={Math.max(12, ry - 5)}
              fontSize={10} fill={isSelected ? '#000' : '#fff'}
              fontFamily="system-ui, sans-serif"
              fontWeight={isSelected ? 700 : 400}
            >
              {label}
            </text>

            {/* Corner handles when selected */}
            {isSelected && [
              [rx, ry], [rx + rw, ry], [rx, ry + rh], [rx + rw, ry + rh]
            ].map(([hx, hy], hi) => (
              <rect key={hi} x={hx - 4} y={hy - 4} width={8} height={8} fill="#facc15" rx={2} />
            ))}
          </g>
        )
      })}
    </>
  )
}
