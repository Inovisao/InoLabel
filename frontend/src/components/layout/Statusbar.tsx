import { useAnnotationStore } from '@/stores/annotationStore'
import { useUIStore } from '@/stores/uiStore'

export function Statusbar() {
  const state = useAnnotationStore(s => s.state)
  const canvasMode = useUIStore(s => s.canvasMode)

  const src = state
    ? `${state.video_name}  [${state.current_source_index + 1}/${state.total_sources}]  ·  Frame ${state.frame_index}`
    : '—'

  const roi = state?.roi_defined
    ? '✓ ROI'
    : `ROI ${state?.roi_points?.length ?? 0}/4`

  const modeLabel = {
    validate: 'Validação',
    draw: '● Anotação',
    select: '● Seleção',
    remove: '● Remoção',
    pan: '● Pan',
    roi: '● ROI',
  }[canvasMode]

  const saved = state?.total_saved ?? 0
  const zoom = state ? `${Math.round(state.zoom_scale * 100)}%` : '100%'

  return (
    <footer className="flex items-center h-8 px-4 bg-slate-900 border-t border-slate-700/60 gap-4 text-xs text-slate-400 flex-shrink-0">
      <span className="truncate max-w-xs">{src}</span>
      <span className="text-slate-600">|</span>
      <span className={state?.roi_defined ? 'text-blue-400' : ''}>{roi}</span>
      <span className="text-slate-600">|</span>
      <span className="text-slate-300">{modeLabel}</span>
      <span className="text-slate-600">|</span>
      <span>{saved} salvos</span>
      <span className="text-slate-600">|</span>
      <span>Zoom {zoom}</span>
      {state?.in_review && (
        <>
          <span className="text-slate-600">|</span>
          <span className="text-amber-400 font-medium">REVISÃO</span>
        </>
      )}
    </footer>
  )
}
