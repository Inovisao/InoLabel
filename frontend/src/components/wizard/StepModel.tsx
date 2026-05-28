import { useState } from 'react'
import { Plus, X, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { useAnnotationStore } from '@/stores/annotationStore'
import { WizardNav } from './WizardNav'

export function StepModel() {
  const { wizardData, setWizardData, setWizardStep, buildStartRequest } = useSessionStore()
  const setAnnotationState = useAnnotationStore(s => s.setState)
  const setPhase = useSessionStore(s => s.setPhase)

  const [modelPath, setModelPath] = useState(wizardData.weights_paths?.[0] ?? '')
  const [classes, setClasses] = useState<string[]>(wizardData.target_classes ?? [])
  const [newClass, setNewClass] = useState('')
  const [confidence, setConfidence] = useState(wizardData.confidence_threshold ?? 0.4)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const addClass = () => {
    const name = newClass.trim()
    if (!name || classes.includes(name)) return
    setClasses(prev => [...prev, name])
    setNewClass('')
  }

  const removeClass = (c: string) => setClasses(prev => prev.filter(x => x !== c))

  const start = async () => {
    if (!classes.length) { setError('Adicione ao menos uma classe'); return }
    setError('')
    setWizardData({
      weights_paths: modelPath.trim() ? [modelPath.trim()] : [],
      target_classes: classes,
      confidence_threshold: confidence,
    })
    const req = buildStartRequest()
    if (!req) { setError('Configuração incompleta'); return }
    req.target_classes = classes
    req.weights_paths = modelPath.trim() ? [modelPath.trim()] : []
    req.confidence_threshold = confidence
    setLoading(true)
    try {
      const state = await api.session.start(req)
      setAnnotationState(state)
      setPhase('annotating')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg || 'Falha ao iniciar sessão')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-1">Modelo & Classes</h2>
      <p className="text-slate-400 text-sm mb-6">
        Configure o modelo YOLO e as classes a anotar
      </p>

      <label className="text-slate-300 text-sm font-medium block mb-2">
        Modelo YOLO <span className="text-slate-500 font-normal">(opcional — anotação manual sem modelo)</span>
      </label>
      <input
        className="w-full bg-slate-800 border border-slate-600 focus:border-blue-500 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-500 outline-none transition-colors mb-5"
        placeholder="Ex: model.pt ou C:\models\yolov8n.pt"
        value={modelPath}
        onChange={e => setModelPath(e.target.value)}
      />

      <label className="text-slate-300 text-sm font-medium block mb-2">Classes *</label>
      <div className="flex gap-2 mb-3">
        <input
          className="flex-1 bg-slate-800 border border-slate-600 focus:border-blue-500 rounded-lg px-3 py-2 text-white text-sm placeholder:text-slate-500 outline-none transition-colors"
          placeholder="Nome da classe"
          value={newClass}
          onChange={e => setNewClass(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addClass()}
        />
        <button
          onClick={addClass}
          className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus size={16} />
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-5 min-h-8">
        {classes.map((c, i) => (
          <span
            key={i}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-600/20 border border-blue-500/50 text-blue-300 text-xs rounded-full"
          >
            {c}
            <button onClick={() => removeClass(c)} className="text-blue-400 hover:text-white">
              <X size={12} />
            </button>
          </span>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-6">
        <label className="text-slate-300 text-sm font-medium w-32">
          Confiança: <span className="text-blue-400">{Math.round(confidence * 100)}%</span>
        </label>
        <input
          type="range" min={0} max={1} step={0.05}
          value={confidence}
          onChange={e => setConfidence(Number(e.target.value))}
          className="flex-1 accent-blue-500"
        />
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      <WizardNav
        onBack={() => setWizardStep(2)}
        onNext={start}
        nextLabel={loading ? undefined : 'Iniciar'}
        nextIcon={loading ? <Loader2 size={16} className="animate-spin" /> : undefined}
        disabled={loading}
      />
    </div>
  )
}
