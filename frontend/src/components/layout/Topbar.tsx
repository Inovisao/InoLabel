import { HelpCircle, Download, LogOut } from 'lucide-react'
import { useAnnotationStore } from '@/stores/annotationStore'
import { useUIStore } from '@/stores/uiStore'
import { useSessionStore } from '@/stores/sessionStore'
import { api } from '@/lib/api'

const MODE_COLORS: Record<string, string> = {
  tracking: 'bg-violet-600',
  detection: 'bg-blue-600',
  obb: 'bg-amber-600',
  classification: 'bg-emerald-600',
}

const MODE_LABELS: Record<string, string> = {
  tracking: 'Tracking',
  detection: 'Detecção',
  obb: 'OBB',
  classification: 'Classificação',
}

export function Topbar() {
  const state = useAnnotationStore(s => s.state)
  const { setShowKeybindHelp, setShowExportDialog } = useUIStore()
  const setPhase = useSessionStore(s => s.setPhase)

  const quit = async () => {
    await api.session.stop().catch(() => {})
    setPhase('wizard')
  }

  const mode = state?.mode ?? 'detection'

  return (
    <header className="flex items-center h-11 px-4 bg-slate-900 border-b border-slate-700/60 gap-3 flex-shrink-0">
      {/* Mode badge */}
      <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${MODE_COLORS[mode] ?? 'bg-slate-700'}`}>
        {MODE_LABELS[mode] ?? mode}
      </span>

      {/* Status */}
      <span className="text-slate-300 text-sm truncate flex-1">
        {state?.status_message ?? '—'}
      </span>

      {/* Info message */}
      {state?.info && (
        <span className="text-slate-400 text-xs truncate max-w-xs">{state.info}</span>
      )}

      <div className="flex items-center gap-1">
        <button
          onClick={() => setShowExportDialog(true)}
          title="Exportar dataset (E)"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
        >
          <Download size={16} />
        </button>
        <button
          onClick={() => setShowKeybindHelp(true)}
          title="Atalhos de teclado (F1)"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
        >
          <HelpCircle size={16} />
        </button>
        <button
          onClick={quit}
          title="Sair"
          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  )
}
