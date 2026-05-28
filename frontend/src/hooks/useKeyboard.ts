import { useEffect } from 'react'
import { api } from '@/lib/api'
import { useAnnotationStore } from '@/stores/annotationStore'
import { useUIStore } from '@/stores/uiStore'
import { useSessionStore } from '@/stores/sessionStore'

export function useKeyboard() {
  const setState = useAnnotationStore(s => s.setState)
  const setShowExportDialog = useUIStore(s => s.setShowExportDialog)
  const setShowKeybindHelp = useUIStore(s => s.setShowKeybindHelp)
  const phase = useSessionStore(s => s.phase)

  useEffect(() => {
    if (phase !== 'annotating') return

    const handler = async (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return

      const key = e.key
      const ctrl = e.ctrlKey || e.metaKey

      try {
        let next = null
        if (key === 'Enter') next = await api.frame.accept()
        else if (key === ' ') { e.preventDefault(); next = await api.frame.reject() }
        else if (ctrl && key === 'z') next = await api.frame.undo()
        else if (key === 'F1' || key === '?') { setShowKeybindHelp(true); return }
        else if (key === 'Escape') { setShowExportDialog(false); setShowKeybindHelp(false); return }

        if (next) setState(next)
      } catch { /* ignore */ }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [phase, setState, setShowExportDialog, setShowKeybindHelp])
}
