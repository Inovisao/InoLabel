interface Props {
  points: [number, number][]
  pendingPoints: [number, number][]
  imgW: number
  imgH: number
}

export function ROIOverlay({ points, pendingPoints, imgW, imgH }: Props) {
  const allPoints = points.length === 4 ? points : pendingPoints

  if (!allPoints.length) return null

  const scaled = allPoints.map(([x, y]) => [x * imgW, y * imgH] as [number, number])
  const isClosed = allPoints.length === 4

  return (
    <g>
      {scaled.length >= 2 && Array.from({ length: scaled.length - 1 }).map((_, i) => (
        <line
          key={i}
          x1={scaled[i][0]} y1={scaled[i][1]}
          x2={scaled[i + 1][0]} y2={scaled[i + 1][1]}
          stroke="#3b82f6" strokeWidth={2}
        />
      ))}
      {isClosed && (
        <line
          x1={scaled[3][0]} y1={scaled[3][1]}
          x2={scaled[0][0]} y2={scaled[0][1]}
          stroke="#3b82f6" strokeWidth={2}
        />
      )}
      {scaled.map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={6} fill="#3b82f6" fillOpacity={0.8} stroke="#fff" strokeWidth={1.5} />
          <text x={x + 8} y={y - 6} fontSize={10} fill="#3b82f6" fontFamily="system-ui">{i + 1}</text>
        </g>
      ))}
    </g>
  )
}
