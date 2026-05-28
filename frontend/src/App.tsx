import { useSessionStore } from '@/stores/sessionStore'
import { WizardShell } from '@/components/wizard/WizardShell'
import { AppLayout } from '@/components/layout/AppLayout'

export default function App() {
  const phase = useSessionStore(s => s.phase)
  return phase === 'wizard' ? <WizardShell /> : <AppLayout />
}
