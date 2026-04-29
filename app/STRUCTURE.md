# Estrutura de Código

## Entrada

- `main.py` — ponto de entrada da aplicação.
- `app/runner.py` — abre o wizard inicial, cria a sessão e inicia a anotação.

---

## Camadas da aplicação de anotação

O módulo `app/annotation/` segue uma arquitetura em camadas. A dependência flui de fora para dentro: apresentação → aplicação → infraestrutura → domínio.

```
presentation  →  application  →  infrastructure  →  core (domínio)
     ↑                ↑                 ↑                  ↑
  UI, painéis    autosave,          persistência       lógica pura
  controles      encerramento       exportações        sem UI/I-O
```

Cada camada está em sua própria pasta dentro de `app/annotation/`.

---

### Estado e inicialização

- `app/annotation/state/core_init.py` — `__init__` da ferramenta: valida caminhos, carrega modelo, constrói UI e inicia a primeira fonte.
- `app/annotation/state/runtime_state.py` — inicializa todas as variáveis de estado runtime (detecções, zoom, undo stack, tracking state, etc.).
- `app/annotation/state/class_config.py` — re-exporta `ClassConfigMixin` composto por `ClassServiceMixin` + `ClassPanelWidgetMixin`.

---

### Domínio (`core/`)

Lógica pura de negócio — sem UI, sem I/O, sem dependência de Tkinter ou arquivo.

- `app/annotation/core/services/class_service.py` — gerenciamento de categorias: registro, remapeamento de IDs, reordenação, remoção, cor, atalhos de teclado.

---

### Infraestrutura (`infrastructure/`)

Implementações concretas de I/O: leitura/escrita de arquivos, chamadas a bibliotecas externas.

#### Persistência

- `app/annotation/infrastructure/persistence/coco_storage.py` — operações COCO em memória e disco: `store_annotations`, `write_annotations`, `build_coco_payload`, `delete_image_annotations`, etc.
- `app/annotation/infrastructure/persistence/export_actions.py` — ações de exportação disparadas pela UI: salvar `.coco.json`, salvar `.yaml`, exportar dataset completo.

---

### Aplicação (`application/`)

Casos de uso que orquestram domínio + infraestrutura sem conhecer a UI diretamente.

- `app/annotation/application/lifecycle.py` — `autosave_current_frame`, `finish_processing`, `run` (loop Tkinter).

---

### Apresentação (`presentation/`)

Construção de widgets e painéis Tkinter. Nenhuma regra de negócio aqui.

#### Painéis

- `app/annotation/presentation/panels/main_window.py` — orquestração da janela: chama `_build_topbar`, `_build_statusbar`, `_build_body`, `_bind_shortcuts`. Define tema e variáveis UI.
- `app/annotation/presentation/panels/topbar_panel.py` — barra superior (badge de modo, label de info, botões de ação), tooltip de ajuda e diálogo de mapeamento de teclas.
- `app/annotation/presentation/panels/statusbar_panel.py` — barra de status inferior com os cinco blocos informativos.
- `app/annotation/presentation/panels/sidebar_panel.py` — sidebar rolável com todas as seções de botões (Anotação, ID Manual, Classes, Exportar, Sair).
- `app/annotation/presentation/panels/canvas_panel.py` — área do canvas e bind dos eventos de mouse.

#### Widgets

- `app/annotation/presentation/widgets/class_panel_widget.py` — widget de lista de classes com tags coloridas, botões de reordenar/remover e entrada inline de nova classe.

---

### Fontes de mídia (`sources/`)

- `app/annotation/sources/source_discovery.py` — descobre vídeos, pastas de imagens e listas de imagens.
- `app/annotation/sources/source_loading.py` — carrega fontes, registra handlers de sinal, navega entre fontes.
- `app/annotation/sources/source_helpers.py` — reset de estado, retomada de posição, leitura do primeiro frame.

---

### ROI e homografia (`roi/`)

- `app/annotation/roi/roi_state.py` — captura de 4 pontos, cálculo de homografia, salvamento em disco.
- `app/annotation/roi/roi_projection.py` — `warp_frame`, `project_bbox`, `is_inside_roi`.

---

### Detecção e rastreamento (`detection/`)

- `app/annotation/detection/frame_pipeline.py` — processa cada frame: roda modelo, aplica tracking, filtra por ROI, monta objetos `Detection`.
- `app/annotation/detection/frame_model_helpers.py` — inferência YOLO, NMS de ensemble multi-modelo.
- `app/annotation/detection/tracking_ids.py` — geração e matching de `track_id` (ID global, ID manual, histórico recente).
- `app/annotation/detection/selection_edit.py` — undo/redo (stack de snapshots), seleção de detecção, edição de ID e classe.
- `app/annotation/detection/review_nav.py` — cache LRU de frames salvos, navegação de revisão, reconstrução de detecções a partir do JSON.
- `app/annotation/detection/workflow_actions.py` — `on_accept`, `on_reject`, `on_quit`, `on_delete_image`, memória de tracks manuais.
- `app/annotation/detection/persistence.py` — re-exporta `PersistenceMixin` composto por `CocoStorageMixin` + `ExportActionsMixin` + `LifecycleMixin`.

---

### UI — controles e renderização (`ui/`)

Arquivos já focados que não foram divididos.

- `app/annotation/ui/ui_layout.py` — re-exporta `UILayoutMixin` composto pelos cinco painéis de `presentation/panels/`.
- `app/annotation/ui/ui_controls.py` — bind de atalhos de teclado, mapeamento de teclas, estado dos botões.
- `app/annotation/ui/display_canvas.py` — renderização do frame no canvas, zoom, pan, coordenadas imagem↔canvas.
- `app/annotation/ui/display_overlays.py` — desenho de bounding boxes e overlay de ROI no canvas.
- `app/annotation/ui/display_status.py` — atualização dos blocos de status, label de imagem, botão "Ver em folder".
- `app/annotation/ui/mouse_events.py` — eventos de mouse: desenhar caixa, selecionar, remover, pan, zoom.
- `app/annotation/ui/mode_toggles.py` — alternância exclusiva de modos (anotação, remoção, seleção, editar ID, pan).

---

### Composição principal

- `app/annotation/tool.py` — define `AnnotationTool` compondo todos os mixins por camada, com comentários que indicam a origem de cada capacidade.

---

## Fora do módulo de anotação

- `app/core/session.py` — `AnnotationSessionConfig` e `AnnotationTaskMode`.
- `app/models.py` — dataclasses `Detection` e `ByteTrackerArgs`.
- `app/geometry.py` — utilitários geométricos (`bbox_iou`, `clip_bbox`, `order_points`, etc.).
- `app/dataset_export.py` — `export_detection_coco_json` e `export_yolo_dataset`.
- `app/config.py` — constantes e defaults de configuração.
- `app/tracking/multiclass_byte_tracking.py` — `BYTETracker` independente por classe.
- `app/ui/theme.py` — tokens de cores, fontes, espaçamentos e tamanhos.
- `app/ui/startup/wizard.py` — wizard de 3 etapas para configurar a sessão.
- `app/sources/discovery.py` — descoberta de fontes independente de UI.

---

## Testes

- `tests/test_session_config.py` — sessão e descoberta de fontes.
- `tests/test_scale.py` e `tests/test_theme.py` — escala visual e tokens de tema.
- `tests/test_dataset_export.py` — exportação, persistência e workflow.
