import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

interface WizardNavProps {
  onBack?: () => void
  onNext?: () => void
  nextLabel?: string
  nextIcon?: ReactNode
  disabled?: boolean
}

export function WizardNav({ onBack, onNext, nextLabel = 'Próximo', nextIcon, disabled }: WizardNavProps) {
  return (
    <div className="flex justify-between items-center mt-8 pt-6 border-t border-slate-700">
      {onBack ? (
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-slate-400 hover:text-white text-sm transition-colors"
        >
          <ChevronLeft size={16} /> Voltar
        </button>
      ) : <div />}

      {onNext && (
        <button
          onClick={onNext}
          disabled={disabled}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors"
        >
          {nextIcon ?? null}
          {nextLabel}
          {!nextIcon && <ChevronRight size={16} />}
        </button>
      )}
    </div>
  )
}
