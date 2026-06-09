# InoLabel — Instruções para Agentes

## O que é este projeto

InoLabel é uma ferramenta desktop de anotação de imagens para visão computacional.
Stack: FastAPI (Python) + React/TypeScript + PyInstaller (empacota tudo em um `.exe`).
O backend roda em `127.0.0.1:8765` e serve o frontend compilado como static files.
Há suporte a Tauri, mas o fluxo principal é via browser + uvicorn.

## Arquitetura em 30 segundos

```
main.py           → inicia uvicorn + abre browser
app/api/main.py   → FastAPI, monta todas as rotas
app/api/state.py  → estado em memória (sessões, frames, anotações, exports)
app/api/routes/   → session, frames, annotations, export, classes, browse, keybinds
app/core/         → ExportJob, lógica de export compartilhada
app/annotation/   → exporters YOLO/COCO, split, augmentation
frontend/src/     → React + Zustand + Vite
build.ps1         → npm run build → PyInstaller → APLICATIVO/InoLabel/InoLabel.exe
```

## Modos de anotação

| Modo           | O que faz                                      |
|----------------|------------------------------------------------|
| detection      | bbox manual ou via YOLO, sem tracking          |
| tracking       | bbox + track_id via BYTETracker                |
| obb            | bounding box orientado (ângulo)                |
| classification | copia frame para subpasta por classe           |

## Arquivos críticos — leia antes de mexer

- `app/api/state.py` — registros globais: `_sessions`, `_exports`, `annotation_store`, `frame_paths`
- `app/api/routes/session.py` — lifecycle da sessão + endpoint `/projects`
- `app/api/routes/export.py` — `_run_export()` (background task)
- `app/api/schemas.py` — todos os modelos Pydantic da API
- `app/annotation/infrastructure/export/yolo_exporter.py` — exportador YOLO
- `app/annotation/infrastructure/export/coco_exporter.py` — exportador COCO
- `frontend/src/stores/session.ts` — Zustand: sessão ativa
- `frontend/src/stores/annotation.ts` — Zustand: frames e anotações
- `frontend/src/api/client.ts` — wrapper fetch para `/api/*`

## Workflows obrigatórios

### Feature nova
1. Leia os arquivos críticos afetados
2. Escreva uma especificação (o quê, por quê, casos de borda)
3. Escreva o plano técnico (quais arquivos mudam, ordem das mudanças)
4. Divida em tarefas pequenas e independentes
5. Implemente uma tarefa de cada vez
6. Ao terminar: rode `npm run build` no frontend e verifique TypeScript

### Bug fix
1. Reproduza o bug antes de tocar no código
2. Identifique a causa raiz (não trate sintomas)
3. Corrija e explique exatamente o que estava errado

### Mudança de UI
1. Siga os tokens do design system (`var(--color-*)`, `var(--radius-*)`, `var(--font-*)`)
2. Não use valores hardcoded de cor, tamanho ou fonte
3. Veja `frontend/AGENTS.md` para padrões de componente

### Mudança de API
1. Altere schema Pydantic em `app/api/schemas.py` primeiro
2. Depois rota, depois frontend
3. Veja `app/AGENTS.md` para padrões de rota

## Build e empacotamento

```powershell
# Gera o exe completo (faz npm run build automaticamente)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build.ps1
```

O script:
1. Valida pré-requisitos
2. Cria env conda `inolabel` se não existir
3. Instala Python deps
4. Roda `npm install` + `npm run build` no frontend
5. Roda PyInstaller → `APLICATIVO/InoLabel/InoLabel.exe`

**Nunca suba `frontend/dist/` nem `APLICATIVO/` para o git.**

## Padrões que NÃO devem ser quebrados

- Estado em memória fica em `app/api/state.py` — não espalhado pelos routes
- Anotações são autosalvas em `.txt` a cada mutação (não em batch)
- Sessão produz `.inolabel.json` no `output_path` para o Projects/History page
- A sessão ativa é única: `active_session()` retorna no máximo uma
- Rota `/api/session/projects` scan subdirs de um path — não recursivo além de 1 nível
- Frontend usa `api.get/post/delete` do `client.ts` — nunca fetch direto

## Ao terminar qualquer tarefa

- Rode `tsc --noEmit` dentro de `frontend/` para checar tipos
- Explique exatamente quais arquivos foram alterados e por quê
- Se mexeu em rota: liste o método + path novo/alterado
- Se mexeu em schema: liste os campos adicionados/removidos
