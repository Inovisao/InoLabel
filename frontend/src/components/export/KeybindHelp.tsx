import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'

const BINDS = [
  { group: 'Fluxo', items: [
    { key: 'Enter', desc: 'Validar frame' },
    { key: 'Space', desc: 'Pular frame' },
    { key: 'Ctrl+Z', desc: 'Desfazer' },
  ]},
  { group: 'Modos', items: [
    { key: 'K', desc: 'Anotar manual (on/off)' },
    { key: 'S', desc: 'Selecionar (on/off)' },
    { key: 'H', desc: 'Pan (on/off)' },
    { key: 'R', desc: 'Definir ROI' },
  ]},
  { group: 'Geral', items: [
    { key: '1–9', desc: 'Selecionar classe' },
    { key: 'F1 / ?', desc: 'Esta ajuda' },
    { key: 'Esc', desc: 'Fechar diálogos' },
  ]},
]

export function KeybindHelp() {
  const { showKeybindHelp, setShowKeybindHelp } = useUIStore()

  return (
    <AnimatePresence>
      {showKeybindHelp && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowKeybindHelp(false)}
          />
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.18 }}
          >
            <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-md p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-semibold text-white">Atalhos de Teclado</h2>
                <button onClick={() => setShowKeybindHelp(false)} className="text-slate-400 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-5">
                {BINDS.map(({ group, items }) => (
                  <div key={group}>
                    <p className="text-slate-500 text-[10px] font-semibold uppercase tracking-widest mb-2">{group}</p>
                    <div className="space-y-1.5">
                      {items.map(({ key, desc }) => (
                        <div key={key} className="flex items-center justify-between">
                          <span className="text-slate-300 text-sm">{desc}</span>
                          <kbd className="px-2 py-0.5 bg-slate-800 border border-slate-600 text-slate-300 text-xs rounded font-mono">
                            {key}
                          </kbd>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
