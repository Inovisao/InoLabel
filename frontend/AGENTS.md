# Frontend Agent — frontend/src/

Você está no frontend React/TypeScript do InoLabel. Leia isto antes de qualquer mudança.

## Stack

- React 18 + TypeScript + Vite
- Zustand para estado global
- Radix UI para componentes primitivos (Dialog, DropdownMenu, Select, Slider, Switch, Tooltip)
- Lucide React para ícones
- `api/client.ts` para todas as chamadas HTTP

## Design system — tokens obrigatórios

Nunca hardcode cores, raios ou fontes. Use sempre variáveis CSS:

```css
/* Cores */
--color-primary          /* indigo-600 #4F46E5 — ações principais */
--color-primary-light    /* fundo sutil em itens selecionados */
--color-bg               /* fundo da página */
--color-panel            /* fundo de cards e modais */
--color-border           /* bordas e divisores */
--color-text             /* texto principal */
--color-muted            /* texto secundário / labels */
--color-danger           /* erros e ações destrutivas */
--color-hero-bg          /* fundo do hero / hover sutil */

/* Raios */
--radius-sm  --radius-md  --radius-lg  --radius-xl

/* Fontes */
--font-sans   /* Inter */
--font-mono   /* SFMono */
```

## Classes utilitárias (CSS global)

```css
.btn-primary     /* botão ação principal */
.btn-secondary   /* botão ação secundária */
.btn-icon        /* botão só com ícone */
.input           /* campo de texto */
.text-display    /* título de página */
.text-page-subtitle
.text-label      /* label de formulário */
.text-helper     /* texto auxiliar abaixo de label */
```

## Estrutura de arquivos

```
src/
  api/
    client.ts          ← ÚNICO ponto de fetch: api.get/post/delete
    types.ts           ← interfaces TypeScript espelhando os schemas Pydantic
  stores/
    session.ts         ← sessão ativa, start/stop/recover
    annotation.ts      ← frame atual, classes, anotações, navegação
  pages/
    WizardPage.tsx     ← onboarding (3 steps: Mode → Data → Config)
    AnnotatePage.tsx   ← tela principal de anotação
    ProjectsPage.tsx   ← grid de projetos com resume
    HistoryPage.tsx    ← lista cronológica com resume
    HelpPage.tsx
    ShortcutsPage.tsx
  components/
    canvas/AnnotationCanvas.tsx   ← canvas Konva, draw bbox/obb
    layout/Topbar.tsx             ← barra superior com Export/Settings/Stop
    layout/Sidebar.tsx            ← lista de classes + navegação de frames
    layout/Statusbar.tsx          ← info de frame atual
    layout/NavSidebar.tsx         ← navegação entre páginas
    layout/PageShell.tsx          ← wrapper de página com NavSidebar
    wizard/StepMode.tsx           ← seletor de modo de anotação
    wizard/StepData.tsx           ← seletor de pasta + output
    wizard/StepConfig.tsx         ← classes + modelo + confiança
    modals/ExportModal.tsx        ← export com formato + split + progresso
    modals/SettingsModal.tsx
    modals/ConfirmModal.tsx
  hooks/useKeyboardShortcuts.ts
  ui/ToastContext.tsx
```

## Stores Zustand

### `useSessionStore` (`stores/session.ts`)
```typescript
{ active, sessionId, mode, classes, totalFrames, currentIndex }
start(req)   // POST /session/start → GET /frames/init
stop()       // POST /session/stop
recover()    // GET /session/status — chamado no App mount para reconectar
```

### `useAnnotationStore` (`stores/annotation.ts`)
```typescript
{ frame, classes, selectedClass, loading }
fetchFrame()         // GET /frames/current
fetchClasses()       // GET /classes
nextFrame()          // POST /frames/next
prevFrame()          // POST /frames/prev
addAnnotation(...)   // POST /annotations/{image_id}
deleteAnnotation(...)// DELETE /annotations/{image_id}/{ann_id}
```

## API client

```typescript
import { api } from "../api/client";

// GET
const data = await api.get<ProjectEntry[]>("/session/projects?path=...");

// POST com body
const { export_id } = await api.post<{ export_id: string }>("/export", { ... });

// DELETE
await api.delete(`/annotations/${imageId}/${annId}`);
```

O `BASE` é `/api`, então `/export` vira `/api/export`.
Erros HTTP são lançados como `Error` com a mensagem do campo `detail`.

## Adicionando um novo formato de export

1. Adicione entrada em `FORMATS` no `ExportModal.tsx`
2. Remova `soon: true` do objeto (ou não adicione)
3. Adicione o tipo em `ExportFormat` se necessário
4. Implemente o backend (ver `app/AGENTS.md`)

## Adicionando uma nova página

1. Crie `src/pages/NovaPagina.tsx` usando `<PageShell>` como wrapper
2. Adicione o tipo em `AppView` em `App.tsx`
3. Adicione a rota no bloco de renderização em `App.tsx`
4. Adicione o item de navegação em `NavSidebar.tsx`

## Padrão de modal

Todos os modais usam `@radix-ui/react-dialog`:

```tsx
<Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
  <Dialog.Portal>
    <Dialog.Overlay style={{ position: "fixed", inset: 0, ... }} />
    <Dialog.Content style={{ position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)", ... }}>
      <Dialog.Title>...</Dialog.Title>
      <Dialog.Description>...</Dialog.Description>
      {/* conteúdo */}
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

## Padrão de layout de página

```tsx
export default function MinhaPage({ activeNav, onNavigate }: Props) {
  return (
    <PageShell activeNav={activeNav} onNavigate={onNavigate} breadcrumb="Minha Página">
      {/* Hero */}
      <div style={{ background: "var(--color-hero-bg)", borderRadius: "var(--radius-xl)", padding: "28px 32px", marginBottom: 24 }}>
        <h1 className="text-display">Título</h1>
        <p className="text-page-subtitle">Subtítulo</p>
      </div>
      {/* conteúdo */}
    </PageShell>
  );
}
```

## Tipos TypeScript (`api/types.ts`)

Espelham os schemas Pydantic do backend. Sempre atualize os dois juntos:

```
SessionStartRequest  ↔  SessionStartRequest (schemas.py)
SessionStatus        ↔  get_legacy_status() response
ProjectEntry         ↔  ProjectEntry (schemas.py)
Annotation           ↔  Annotation (schemas.py)
FrameResponse        ↔  FrameResponse (schemas.py)
ClassItem            ↔  ClassItem (schemas.py)
```

## O que NÃO fazer

- Nunca chame `fetch` diretamente — sempre use `api.get/post/delete`
- Não use `useState` para estado que é compartilhado entre componentes — use Zustand
- Não hardcode cores, raios ou fontes — use tokens CSS
- Não crie componentes com `style` de layout duplicado — reutilize `PageShell`, `btn-primary`, `.input`
- Não use `any` em TypeScript — se a API retorna algo não tipado, defina a interface
- Nunca comite `frontend/dist/` — é gerado pelo build

## Ao terminar uma mudança de frontend

```bash
cd frontend
npx tsc --noEmit   # verifica tipos
npm run build      # verifica build completo
```
