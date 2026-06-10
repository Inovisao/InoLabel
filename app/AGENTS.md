# Backend Agent — app/

Você está no backend FastAPI do InoLabel. Leia isto antes de qualquer mudança.

## Stack e convenções

- Python 3.9+, FastAPI, Pydantic v2, uvicorn
- Todos os modelos ficam em `app/api/schemas.py` — nunca defina modelos inline nos routes
- Routes são registrados em `app/api/main.py` via `app.include_router(...)`
- Prefixos das rotas: `/api/session`, `/api/frames`, `/api/annotations`, `/api/export`, `/api/classes`, `/api/browse`, `/api/keybinds`

## Estado em memória (`app/api/state.py`)

Este é o ponto central de estado do processo. Entenda antes de tocar:

```python
_sessions: dict[str, SessionState]      # sessões ativas/paradas
_exports: dict[str, ExportJob]          # jobs de export em andamento

frame_paths: list[Path]                 # caminhos dos frames do dataset atual
frame_dims: dict[int, tuple[int,int]]   # (width, height) por índice de frame
annotation_store: dict[int, list]       # anotações por índice de frame
next_ann_id: list[int]                  # contador de IDs (list para mutabilidade sem global)
```

**Regras:**
- Nunca importe `_sessions` ou `_exports` diretamente — use as funções `active_session()`, `get_session()`, `create_export()`, etc.
- `annotation_store` é compartilhado entre `frames.py` e `annotations.py` — não recrie em outros módulos
- `reset_annotations()` deve ser chamado no início E no fim de cada sessão

## Lifecycle de uma sessão

```
POST /api/session/start
  → valida inputs
  → stop sessão anterior (se existir)
  → reset_annotations()
  → create_session(...)
  → escreve .inolabel.json no output_path
  → retorna SessionStartResponse

GET /api/frames/init
  → _load_frame_paths() (preenche frame_paths)
  → _current_index restaurado de session.current_frame (0 em nova sessão)
  → reseta _loaded_from_disk, _frame_b64_cache, _prefetching
  → retorna {"total": N, "current_index": K}

GET/POST /api/frames/current|next|prev|goto/{index}
  → _lazy_load_from_disk() carrega .txt do disco na primeira visita
  → next/prev/goto chamam _sync_session_frame() → session.current_frame = _current_index

POST/DELETE /api/annotations/{image_id}
  → atualiza annotation_store
  → chama _autosave() → escreve .txt imediatamente

POST /api/session/stop (ou /{id}/stop)
  → remove_session()
  → _update_project_meta() → atualiza .inolabel.json
  → reset_annotations()
```

## Export pipeline

O export roda como background task no FastAPI:

1. `POST /api/export` → cria `ExportJob`, dispara `_run_export(export_id)` via `asyncio.to_thread` (I/O nunca bloqueia o event loop)
2. `_run_export_blocking` em `app/api/routes/export.py`:
   - Carrega anotações pendentes do disco com PIL header-only read (sem decode completo)
   - Monta `source_image_map: dict[str, Path]` (export_name → caminho original) — **sem staging, zero cópias intermediárias**
   - Passa o mapa diretamente: `"yolo"` → `export_yolo_dataset/no_split`, `"coco"` → `export_detection_coco_json`
   - Cada exporter copia direto da fonte para o destino final usando `ThreadPoolExecutor` (paralelo)
3. `GET /api/export/{id}/progress` → frontend faz polling a cada 500ms

**Não use `tempdir` ou `shutil` no routes/export.py** — o pipeline atual é zero-staging.
Ao adicionar suporte a um novo formato, receba `source_image_map` como parâmetro opcional e delegue cópias ao `ThreadPoolExecutor` interno do exporter.

**Ao adicionar um novo formato de export:**
- Adicione o exporter em `app/annotation/infrastructure/export/`
- Conecte em `_run_export()` com `if "formato" in job.formats:`
- Atualize `ExportRequest` em `schemas.py` se precisar de novos campos
- Remova o `soon: true` correspondente no `ExportModal.tsx`

## Padrões de rota

```python
# Rota que pode colidir com parâmetro de path: defina ANTES
@router.get("/projects")           # ← antes de /{session_id}/status
@router.get("/{session_id}/status")

# Response model sempre explícito
@router.post("/start", response_model=SessionStartResponse)

# Operações bloqueantes de I/O: use run_in_threadpool
total = await run_in_threadpool(_count_frames, data_path)

# Background tasks (sem bloquear a resposta)
background_tasks.add_task(_run_export, job.export_id)
```

## Design de API e interfaces

Antes de criar ou alterar qualquer rota, schema Pydantic, função de serviço, payload de export, store frontend ou método em `frontend/src/api/client.ts`, defina o contrato primeiro.

Use este checklist:

- Consumidor: qual tela, store, exporter ou integração chama isso?
- Responsabilidade: qual recurso ou comportamento a interface expõe?
- Entrada: body, query params, path params ou argumentos tipados.
- Saída: response model/DTO estável, sem expor modelo interno acidentalmente.
- Erros: status HTTP esperado e `detail` amigável; não vaze stack trace, path sensível ou segredo.
- Validação: regras no schema Pydantic quando forem de request/response; não espalhe validação nos routes.
- Compatibilidade: mudança é aditiva ou quebra algum consumidor existente?
- Verificação: teste manual, teste automatizado ou typecheck que prova o contrato.

Template mínimo para mudanças observáveis:

```md
### Contrato: nome-da-interface
- Consumidor:
- Endpoint/função:
- Entrada:
- Saída:
- Erros:
- Validação:
- Compatibilidade:
- Verificação:
```

Regras específicas do InoLabel:

- Endpoints REST usam substantivos e prefixos existentes (`/api/session`, `/api/frames`, etc.); evite verbos no path.
- `response_model` deve ser explícito para respostas estruturadas.
- Tipos TypeScript em `frontend/src/api/types.ts` devem espelhar os schemas Pydantic quando o frontend consumir o contrato.
- Listagens que podem crescer devem ter limite, paginação ou justificativa explícita para não paginar.
- Operações repetíveis devem ser idempotentes quando possível, especialmente `DELETE` e stop/retry de sessão/export.
- Dados de terceiros, paths vindos do usuário e conteúdo lido do disco são input não confiável; valide antes de usar.

## Validação e erros

- HTTPException(422) para input inválido do usuário
- HTTPException(404) para recursos não encontrados
- Nunca deixe exceção vazar sem tratar — no máximo logar e retornar erro amigável
- Validators Pydantic ficam no schema, não no route

## .inolabel.json — estrutura do projeto salvo

```json
{
  "session_id": "uuid",
  "mode": "detection|tracking|obb|classification",
  "data_path": "/caminho/absoluto/dataset",
  "classes": ["classe1", "classe2"],
  "current_frame": 42,
  "created_at": "2024-...",
  "last_modified": "2024-..."
}
```

- Escrito em `start_session` (preserva `created_at` se já existir; inclui `current_frame`)
- Atualizado em `stop_session` via `_update_project_meta()` (salva `current_frame` atual)
- Lido em `start_session` com `resume=True` para restaurar `current_frame`
- O endpoint `/api/session/projects?path=X` escaneia subdirs de X procurando por este arquivo

## Adicionando um novo modo de anotação

1. Adicione o valor em `TaskMode` enum em `schemas.py`
2. Implemente a lógica em `app/annotation/{modo}/`
3. Registre no `start_session` se precisar de inicialização especial
4. Atualize `MODE_LABELS` no frontend (`HistoryPage.tsx`, `ProjectsPage.tsx`)
5. Adicione o card de modo em `StepMode.tsx`

## O que NÃO fazer

- Não use estado global fora de `app/api/state.py`
- Não faça I/O de disco no event loop — use `run_in_threadpool`
- Não importe módulos Tkinter/GUI na árvore `app/api/` — coexistência frágil
- Não altere `annotation_store` fora de `annotations.py` (exceto export e reset)
- Não faça rollback parcial de sessão — se falhar, falhe completamente com erro claro
