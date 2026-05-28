import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Download, Loader2 } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/lib/api'

export function ExportDialog() {
  const { showExportDialog, setShowExportDialog } = useUIStore()
  const [trainRatio, setTrainRatio] = useState(0.7)
  const [valRatio, setValRatio] = useState(0.2)
  const [augFactor, setAugFactor] = useState(0)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const testRatio = Math.max(0, +(1 - trainRatio - valRatio).toFixed(2))

  const runExport = async () => {
    setLoading(true); setResult(null); setError(null)
    try {
      const r = await api.export.run({
        train_ratio: trainRatio,
        val_ratio: valRatio,
        test_ratio: testRatio,
        augmentation_factor: augFactor,
      })
      setResult(r.result ?? 'Exportação concluída')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Falha na exportação')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {showExportDialog && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 z-40"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setShowExportDialog(false)}
          />
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.18 }}
          >
            <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-md p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-white">Exportar Dataset</h2>
                <button onClick={() => setShowExportDialog(false)} className="text-slate-400 hover:text-white">
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-5">
                {/* Splits */}
                <div>
                  <p className="text-sm font-medium text-slate-300 mb-3">Divisão do dataset</p>
                  <div className="space-y-3">
                    {[
                      { label: 'Treino', value: trainRatio, set: setTrainRatio },
                      { label: 'Validação', value: valRatio, set: setValRatio },
                    ].map(({ label, value, set }) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className="text-slate-400 text-sm w-20">{label}</span>
                        <input
                          type="range" min={0} max={1} step={0.05}
                          value={value}
                          onChange={e => set(Number(e.target.value))}
                          className="flex-1 accent-blue-500"
                        />
                        <span className="text-white text-sm w-10 text-right">{Math.round(value * 100)}%</span>
                      </div>
                    ))}
                    <div className="flex items-center gap-3">
                      <span className="text-slate-400 text-sm w-20">Teste</span>
                      <div className="flex-1 h-4 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500/60 rounded-full" style={{ width: `${testRatio * 100}%` }} />
                      </div>
                      <span className="text-white text-sm w-10 text-right">{Math.round(testRatio * 100)}%</span>
                    </div>
                  </div>

                  {/* Visual split bar */}
                  <div className="flex h-3 rounded-full overflow-hidden mt-3 gap-0.5">
                    <div className="bg-blue-500 transition-all" style={{ width: `${trainRatio * 100}%` }} />
                    <div className="bg-emerald-500 transition-all" style={{ width: `${valRatio * 100}%` }} />
                    <div className="bg-amber-500 flex-1 transition-all" />
                  </div>
                </div>

                {/* Augmentation */}
                <div>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 text-sm w-40">Aumentação de dados</span>
                    <input
                      type="range" min={0} max={5} step={1}
                      value={augFactor}
                      onChange={e => setAugFactor(Number(e.target.value))}
                      className="flex-1 accent-blue-500"
                    />
                    <span className="text-white text-sm w-6 text-right">
                      {augFactor === 0 ? '—' : `×${augFactor}`}
                    </span>
                  </div>
                </div>
              </div>

              {result && <p className="mt-4 text-green-400 text-sm">✓ {result}</p>}
              {error && <p className="mt-4 text-red-400 text-sm">✗ {error}</p>}

              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setShowExportDialog(false)}
                  className="flex-1 px-4 py-2.5 border border-slate-600 text-slate-300 hover:text-white rounded-xl text-sm transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={runExport}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-colors"
                >
                  {loading ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />}
                  {loading ? 'Exportando...' : 'Exportar'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
