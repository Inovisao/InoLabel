import { create } from 'zustand'
import type { AnnotationState } from '@/lib/types'

interface AnnotationStore {
  state: AnnotationState | null
  setState: (s: AnnotationState) => void
  patchState: (patch: Partial<AnnotationState>) => void
  clear: () => void
}

export const useAnnotationStore = create<AnnotationStore>((set) => ({
  state: null,
  setState: (state) => set({ state }),
  patchState: (patch) => set(s => s.state ? { state: { ...s.state, ...patch } } : {}),
  clear: () => set({ state: null }),
}))
