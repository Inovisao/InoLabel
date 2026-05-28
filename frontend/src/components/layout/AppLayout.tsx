import { useWebSocket } from '@/hooks/useWebSocket'
import { useKeyboard } from '@/hooks/useKeyboard'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { Statusbar } from './Statusbar'
import { AnnotationCanvas } from '../canvas/AnnotationCanvas'
import { ExportDialog } from '../export/ExportDialog'
import { KeybindHelp } from '../export/KeybindHelp'

export function AppLayout() {
  useWebSocket()
  useKeyboard()

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 text-white overflow-hidden">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-hidden">
          <AnnotationCanvas />
        </main>
        <Sidebar />
      </div>
      <Statusbar />
      <ExportDialog />
      <KeybindHelp />
    </div>
  )
}
