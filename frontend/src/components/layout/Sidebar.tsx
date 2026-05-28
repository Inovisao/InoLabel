import { CheckCircle, XCircle, RotateCcw, MousePointer2, Pencil, Trash2, Move, Crosshair } from 'lucide-react'
import { useAnnotationStore } from '@/stores/annotationStore'
import { useUIStore, type CanvasMode } from '@/stores/uiStore'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const CLASS_COLORS = [
  '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6',
  '#06b6d4','#f97316','#14b8a6','#ec4899','#84cc16',
]

interface SidebarButtonProps {
  icon: React.ReactNode
  label: string
  onClick: () => void
  active?: boolean
  variant?: 'primary' | 'danger' | 'default'
  kbd?: string
}

function SidebarButton({ icon, label, onClick, active, variant = 'default', kbd }: SidebarButtonProps) {
  return (
    <button
      onClick={onClick}
      title={kbd ? `${label} (${kbd})` : label}
      className={cn(
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all',
        active && variant === 'default' && 'bg-blue-600 text-white',
        !active && 'text-slate-300 hover:bg-slate-700 hover:text-white',
        variant === 'primary' && !active && 'hover:bg-green-700 hover:text-white',
        variant === 'danger' && !active && 'hover:bg-red-700 hover:text-white',
      )}
    >
      {icon}
      <span className="flex-1 text-left">{label}</span>
      {kbd && <kbd className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">{kbd}</kbd>}
    </button>
  )
}

export function Sidebar() {
  const state = useAnnotationStore(s => s.state)
  const setState = useAnnotationStore(s => s.setState)
  const { canvasMode, setCanvasMode, setShowExportDialog } = useUIStore()

  const act = async (fn: () => Promise<typeof state>) => {
    try { const s = await fn(); if (s) setState(s) } catch { /* ignore */ }
  }

  const toggleMode = (mode: CanvasMode) =>
    setCanvasMode(canvasMode === mode ? 'validate' : mode)

  const categories = state?.categories ?? []
  const isClassification = state?.mode === 'classification'

  return (
    <aside className="w-52 flex flex-col bg-slate-900 border-l border-slate-700/60 flex-shrink-0 overflow-y-auto">

      {/* Ações principais */}
      <div className="p-3 border-b border-slate-700/60">
        <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-widest mb-2 px-1">Fluxo</p>
        <SidebarButton
          icon={<CheckCircle size={15} className="text-green-400" />}
          label="Validar"
          kbd="Enter"
          variant="primary"
          onClick={() => act(api.frame.accept)}
        />
        <SidebarButton
          icon={<XCircle size={15} className="text-slate-400" />}
          label="Pular"
          kbd="Space"
          onClick={() => act(api.frame.reject)}
        />
        <SidebarButton
          icon={<RotateCcw size={15} />}
          label="Desfazer"
          kbd="Ctrl+Z"
          onClick={() => act(api.frame.undo)}
        />
      </div>

      {/* Modos de canvas */}
      {!isClassification && (
        <div className="p-3 border-b border-slate-700/60">
          <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-widest mb-2 px-1">Modo canvas</p>
          <SidebarButton
            icon={<Pencil size={15} />} label="Anotar" kbd="K"
            active={canvasMode === 'draw'}
            onClick={() => toggleMode('draw')}
          />
          <SidebarButton
            icon={<MousePointer2 size={15} />} label="Selecionar" kbd="S"
            active={canvasMode === 'select'}
            onClick={() => toggleMode('select')}
          />
          <SidebarButton
            icon={<Trash2 size={15} />} label="Remover"
            active={canvasMode === 'remove'}
            variant="danger"
            onClick={() => toggleMode('remove')}
          />
          <SidebarButton
            icon={<Move size={15} />} label="Pan" kbd="H"
            active={canvasMode === 'pan'}
            onClick={() => toggleMode('pan')}
          />
          <SidebarButton
            icon={<Crosshair size={15} />} label="Definir ROI" kbd="R"
            active={canvasMode === 'roi'}
            onClick={() => {
              if (canvasMode === 'roi') act(api.frame.resetROI)
              else toggleMode('roi')
            }}
          />
        </div>
      )}

      {/* Classes */}
      {categories.length > 0 && (
        <div className="p-3 flex-1">
          <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-widest mb-2 px-1">Classes</p>
          <div className="space-y-1">
            {categories.map((cat, i) => (
              <div key={cat.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-800">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: CLASS_COLORS[i % CLASS_COLORS.length] }} />
                <span className="text-slate-300 text-xs truncate">{cat.name}</span>
                <kbd className="ml-auto text-[10px] text-slate-500 bg-slate-800 px-1 rounded">{i + 1}</kbd>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export */}
      <div className="p-3 border-t border-slate-700/60">
        <button
          onClick={() => setShowExportDialog(true)}
          className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          Exportar dataset
        </button>
      </div>
    </aside>
  )
}
