import { create } from 'zustand'

export type CanvasMode = 'validate' | 'draw' | 'select' | 'remove' | 'pan' | 'roi'

interface UIStore {
  canvasMode: CanvasMode
  showExportDialog: boolean
  showKeybindHelp: boolean
  showClassPanel: boolean
  setCanvasMode: (m: CanvasMode) => void
  setShowExportDialog: (v: boolean) => void
  setShowKeybindHelp: (v: boolean) => void
  setShowClassPanel: (v: boolean) => void
}

export const useUIStore = create<UIStore>((set) => ({
  canvasMode: 'validate',
  showExportDialog: false,
  showKeybindHelp: false,
  showClassPanel: true,
  setCanvasMode: (canvasMode) => set({ canvasMode }),
  setShowExportDialog: (showExportDialog) => set({ showExportDialog }),
  setShowKeybindHelp: (showKeybindHelp) => set({ showKeybindHelp }),
  setShowClassPanel: (showClassPanel) => set({ showClassPanel }),
}))
