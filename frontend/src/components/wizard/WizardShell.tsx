import { AnimatePresence, motion } from 'framer-motion'
import { useSessionStore } from '@/stores/sessionStore'
import { StepMode } from './StepMode'
import { StepDataset } from './StepDataset'
import { StepOutput } from './StepOutput'
import { StepModel } from './StepModel'

const STEPS = ['Modo', 'Dataset', 'Saída', 'Modelo']

const variants = {
  enter: (dir: number) => ({ x: dir > 0 ? 80 : -80, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir: number) => ({ x: dir > 0 ? -80 : 80, opacity: 0 }),
}

export function WizardShell() {
  const step = useSessionStore(s => s.wizardStep)

  const stepComponents = [<StepMode />, <StepDataset />, <StepOutput />, <StepModel />]

  return (
    <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-slate-950 to-slate-800">
      <div className="w-full max-w-2xl mx-4">

        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-3">
            <img src="/inovisao.png" alt="Inovisão" className="h-8 w-auto opacity-80" onError={e => (e.currentTarget.style.display = 'none')} />
            <h1 className="text-3xl font-bold text-white tracking-tight">InoLabel</h1>
          </div>
          <p className="text-slate-400 text-sm">Ferramenta de anotação de visão computacional</p>
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold transition-all duration-300 ${
                i < step ? 'bg-blue-600 text-white' :
                i === step ? 'bg-white text-slate-900 ring-2 ring-blue-500' :
                'bg-slate-700 text-slate-400'
              }`}>
                {i < step ? '✓' : i + 1}
              </div>
              <span className={`text-xs transition-colors ${i === step ? 'text-white font-medium' : 'text-slate-500'}`}>
                {label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={`w-8 h-px mx-1 transition-colors ${i < step ? 'bg-blue-600' : 'bg-slate-700'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
          <AnimatePresence mode="wait" custom={1}>
            <motion.div
              key={step}
              custom={1}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.22, ease: 'easeInOut' }}
              className="p-8"
            >
              {stepComponents[step]}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
