import { useState } from 'react'
import { FolderOpen, FileJson } from 'lucide-react'
import { api } from '@/lib/api'
import { useSessionStore } from '@/stores/sessionStore'
import { WizardNav } from './WizardNav'

export function StepDataset() {
  const { wizardData, setWizardData, setWizardStep } = useSessionStore()
  const [path, setPath] = useState(wizardData.data_root ?? '')
  const [status, setStatus] = useState<'idle' | 'ok' | 'err'>('idle')
  const [errMsg, setErrMsg] = useState('')
  const [browsing, setBrowsing] = useState(false)
  const [importingCoco, setImportingCoco] = useState(false)
  const [cocoInfo, setCocoInfo] = useState<{ images: number; annotations: number; classes: string[] } | null>(null)

  const validate = async () => {
    if (!path.trim()) { setStatus('err'); setErrMsg('Informe o caminho'); return false }
    try {
      const r = await api.wizard.validatePath(path.trim(), 'dataset')
      if (!r.exists) { setStatus('err'); setErrMsg('Caminho não encontrado'); return false }
      setStatus('ok')
      setWizardData({ data_root: path.trim() })
      return true
    } catch {
      setStatus('err'); setErrMsg('Erro ao verificar caminho'); return false
    }
  }

  const browse = async () => {
    setBrowsing(true)
    try {
      const r = await api.wizard.browseFolder()
      if (r.path) {
        setPath(r.path)
        setStatus('idle')
        setCocoInfo(null)
      }
    } catch {
      // dialog cancelled or error — ignore
    } finally {
      setBrowsing(false)
    }
  }

  const importCoco = async () => {
    setImportingCoco(true)
    try {
      const r = await api.wizard.browseFile('coco')
      if (!r.path) return
      const info = await api.wizard.loadAnnotations(r.path) as {
        task_mode: string | null
        class_names: string[]
        image_count: number
        annotation_count: number
        output_dir: string
        annotations_path: string
      }
      // Use output_dir as data_root if no explicit source path available
      const dataRoot = info.output_dir
      setPath(dataRoot)
      setStatus('ok')
      setCocoInfo({
        images: info.image_count,
        annotations: info.annotation_count,
        classes: info.class_names,
      })
      setWizardData({
        data_root: dataRoot,
        annotations_path: info.annotations_path,
        resume: true,
        target_classes: info.class_names.length ? info.class_names : wizardData.target_classes,
      })
    } catch {
      setStatus('err')
      setErrMsg('Erro ao importar arquivo COCO')
    } finally {
      setImportingCoco(false)
    }
  }

  const next = async () => {
    if (await validate()) setWizardStep(2)
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-1">Dataset</h2>
      <p className="text-slate-400 text-sm mb-6">
        Pasta com vídeos, imagens ou lista de arquivos
      </p>

      <label className="text-slate-300 text-sm font-medium block mb-2">
        Caminho do dataset
      </label>
      <div className="flex gap-2 mb-1">
        <input
          className={`flex-1 bg-slate-800 border rounded-lg px-3 py-2.5 text-white text-sm placeholder:text-slate-500 outline-none transition-colors ${
            status === 'err' ? 'border-red-500 focus:border-red-400' :
            status === 'ok' ? 'border-green-500' : 'border-slate-600 focus:border-blue-500'
          }`}
          placeholder="Ex: C:\datasets\meu_projeto"
          value={path}
          onChange={e => { setPath(e.target.value); setStatus('idle'); setCocoInfo(null) }}
          onKeyDown={e => e.key === 'Enter' && next()}
          autoFocus
        />
        <button
          onClick={browse}
          disabled={browsing || importingCoco}
          title="Abrir explorador de pastas"
          className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 text-sm rounded-lg border border-slate-600 transition-colors whitespace-nowrap"
        >
          <FolderOpen size={15} />
          Pasta
        </button>
        <button
          onClick={importCoco}
          disabled={browsing || importingCoco}
          title="Importar dataset a partir de arquivo COCO JSON"
          className="flex items-center gap-1.5 px-3 py-2.5 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 text-sm rounded-lg border border-slate-600 transition-colors whitespace-nowrap"
        >
          <FileJson size={15} />
          Importar COCO
        </button>
      </div>

      {status === 'err' && <p className="text-red-400 text-xs mt-1.5">{errMsg}</p>}
      {status === 'ok' && !cocoInfo && <p className="text-green-400 text-xs mt-1.5">✓ Caminho válido</p>}
      {cocoInfo && (
        <div className="mt-2 px-3 py-2 bg-blue-600/10 border border-blue-500/30 rounded-lg text-xs text-blue-300 space-y-0.5">
          <p>✓ COCO importado — {cocoInfo.images} imagens · {cocoInfo.annotations} anotações</p>
          {cocoInfo.classes.length > 0 && (
            <p className="text-blue-400">Classes: {cocoInfo.classes.join(', ')}</p>
          )}
        </div>
      )}

      <WizardNav
        onBack={() => setWizardStep(0)}
        onNext={next}
        nextLabel="Próximo"
      />
    </div>
  )
}
