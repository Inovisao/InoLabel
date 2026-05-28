import { useState, useEffect } from 'react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import type { OutputStateInfo } from '@/lib/types'
import { WizardNav } from './WizardNav'

export function StepOutput() {
  const { wizardData, setWizardData, setWizardStep } = useSessionStore()
  const [outputPath, setOutputPath] = useState(wizardData.output_dir ?? '')
  const [existingSessions, setExistingSessions] = useState<OutputStateInfo[]>([])
  const [selectedSession, setSelectedSession] = useState<OutputStateInfo | null>(null)

  useEffect(() => {
    if (wizardData.data_root) {
      api.wizard.outputStates(wizardData.data_root)
        .then(s => setExistingSessions(s as OutputStateInfo[]))
        .catch(() => {})
    }
  }, [wizardData.data_root])

  const next = () => {
    if (selectedSession) {
      setWizardData({
        output_dir: selectedSession.path,
        annotations_path: selectedSession.annotations_path,
        resume: true,
      })
    } else {
      setWizardData({ output_dir: outputPath || undefined, resume: false })
    }
    setWizardStep(3)
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-1">Saída & Retomar</h2>
      <p className="text-slate-400 text-sm mb-6">
        Selecione uma sessão anterior ou crie uma nova pasta de saída
      </p>

      {existingSessions.length > 0 && (
        <div className="mb-5">
          <p className="text-slate-300 text-sm font-medium mb-2">Sessões anteriores</p>
          <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
            {existingSessions.map(s => (
              <button
                key={s.path}
                onClick={() => setSelectedSession(prev => prev?.path === s.path ? null : s)}
                className={`w-full text-left px-3 py-2.5 rounded-lg border text-xs transition-colors ${
                  selectedSession?.path === s.path
                    ? 'border-blue-500 bg-blue-600/20 text-white'
                    : 'border-slate-700 text-slate-300 hover:border-slate-500'
                }`}
              >
                <div className="font-medium truncate">{s.path.split(/[/\\]/).pop()}</div>
                <div className="text-slate-400 mt-0.5 truncate">{s.label}</div>
              </button>
            ))}
          </div>
          <button
            onClick={() => setSelectedSession(null)}
            className="text-xs text-slate-500 hover:text-slate-300 mt-2"
          >
            + Nova sessão
          </button>
        </div>
      )}

      {!selectedSession && (
        <>
          <label className="text-slate-300 text-sm font-medium block mb-2">
            Pasta de saída <span className="text-slate-500 font-normal">(opcional — gerada automaticamente)</span>
          </label>
          <input
            className="w-full bg-slate-800 border border-slate-600 focus:border-blue-500 rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-500 outline-none transition-colors"
            placeholder="Deixe em branco para gerar automaticamente"
            value={outputPath}
            onChange={e => setOutputPath(e.target.value)}
          />
        </>
      )}

      <WizardNav onBack={() => setWizardStep(1)} onNext={next} />
    </div>
  )
}
