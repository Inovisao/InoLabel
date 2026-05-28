import { create } from 'zustand'
import type { AnnotationMode, StartSessionRequest } from '@/lib/types'

interface WizardData {
  mode: AnnotationMode
  data_root: string
  weights_paths: string[]
  target_classes: string[]
  output_dir: string
  resume: boolean
  annotations_path: string
  confidence_threshold: number
}

interface SessionStore {
  phase: 'wizard' | 'annotating'
  wizardStep: number
  wizardData: Partial<WizardData>
  setPhase: (p: 'wizard' | 'annotating') => void
  setWizardStep: (s: number) => void
  setWizardData: (d: Partial<WizardData>) => void
  buildStartRequest: () => StartSessionRequest | null
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  phase: 'wizard',
  wizardStep: 0,
  wizardData: {},

  setPhase: (phase) => set({ phase }),
  setWizardStep: (wizardStep) => set({ wizardStep }),
  setWizardData: (d) => set(s => ({ wizardData: { ...s.wizardData, ...d } })),

  buildStartRequest: () => {
    const { wizardData } = get()
    if (!wizardData.mode || !wizardData.data_root || !wizardData.target_classes?.length) {
      return null
    }
    return {
      mode: wizardData.mode,
      data_root: wizardData.data_root,
      weights_paths: wizardData.weights_paths ?? [],
      target_classes: wizardData.target_classes,
      output_dir: wizardData.output_dir || undefined,
      annotations_path: wizardData.annotations_path || undefined,
      resume_existing_annotations: wizardData.resume ?? false,
      confidence_threshold: wizardData.confidence_threshold ?? 0.4,
    }
  },
}))
