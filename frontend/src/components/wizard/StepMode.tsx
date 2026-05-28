import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import type { AnnotationMode } from '@/lib/types'

const MODE_ICONS: Record<string, string> = {
  tracking: '🎯',
  detection: '📦',
  obb: '🔷',
  classification: '🏷️',
}

const MODE_DESC: Record<string, string> = {
  tracking: 'Mantém identidade de objetos entre frames com BYTETracker',
  detection: 'Bounding boxes por frame, sem IDs de rastreamento',
  obb: 'Caixas rotacionadas com ângulo para objetos orientados',
  classification: 'Classifica imagens em categorias por pasta',
}

export function StepMode() {
  const [modes, setModes] = useState<{ value: string; label: string }[]>([])
  const { wizardData, setWizardData, setWizardStep } = useSessionStore()

  useEffect(() => { api.wizard.modes().then(setModes).catch(() => {}) }, [])

  const select = (value: string) => {
    setWizardData({ mode: value as AnnotationMode })
    setTimeout(() => setWizardStep(1), 180)
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-1">Modo de anotação</h2>
      <p className="text-slate-400 text-sm mb-6">Selecione como você quer anotar seu dataset</p>

      <div className="grid grid-cols-2 gap-3">
        {modes.map((m, i) => (
          <motion.button
            key={m.value}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            onClick={() => select(m.value)}
            className={`group p-4 rounded-xl border text-left transition-all duration-150 ${
              wizardData.mode === m.value
                ? 'border-blue-500 bg-blue-600/20 shadow-lg shadow-blue-500/10'
                : 'border-slate-700 hover:border-slate-500 hover:bg-slate-800'
            }`}
          >
            <div className="text-2xl mb-2">{MODE_ICONS[m.value] ?? '📌'}</div>
            <div className="text-white font-medium text-sm">{m.label}</div>
            <div className="text-slate-400 text-xs mt-1 leading-relaxed">
              {MODE_DESC[m.value] ?? ''}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
