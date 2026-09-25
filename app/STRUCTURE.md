# Estrutura de Código

## Entrada

- `main.py` — ponto de entrada da aplicação.
- `app/runner.py` — desativa o input method do X (ibus) antes do Tk conectar, exibe o splash, abre o wizard, cria a sessão e escolhe a ferramenta pelo modo:

| `AnnotationTaskMode` | Ferramenta | Pacote |
|----------------------|------------|--------|
| `TRACKING`, `DETECTION` | `AnnotationTool` | `app/annotation/` |
| `OBB` | `OBBAnnotationTool` | `app/annotation_obb/` |
| `KEYPOINT` | `KeypointAnnotationTool` | `app/annotation_keypoint/` |
| `CLASSIFICATION` | `ClassificationTool` | `app/classification/` |

- `app/startup_dialog.py` e `app/annotation_tool.py` — wrappers de compatibilidade (re-exportam o wizard e o `AnnotationTool`).

> **Imports tardios:** `torch`/`ultralytics` só devem ser importados quando um modelo é carregado. Importar as ferramentas ou o wizard não pode puxar `torch` (garantido por `tests/test_lazy_torch_import.py`).

---

## Composição por mixins

Cada ferramenta (`tool.py`) é uma classe que herda dezenas de mixins, um por responsabilidade. Os modos OBB e Keypoint **reaproveitam** os mixins genéricos de `app/annotation/` (core init, class service, fontes, ROI, lifecycle, painéis) e substituem apenas os específicos do modo, prefixados com `OBB*` ou `KP*`. A ordem das bases define o MRO: o mixin específico deve vir antes do genérico que ele sobrescreve.

Cada pacote de modo tem um `shared.py` com os imports comuns usados pelos mixins (`from app.<pacote>.shared import *`).

---

## Camadas da aplicação de anotação (`app/annotation/`)

A dependência flui de fora para dentro: apresentação → aplicação → infraestrutura → domínio.

```
presentation  →  application  →  infrastructure  →  core (domínio)
     ↑                ↑                 ↑                  ↑
  UI, painéis    autosave,          persistência       lógica pura
  controles      encerramento       exportações        sem UI/I-O
```

Cada camada está em sua própria pasta dentro de `app/annotation/`.

---

### Estado e inicialização

- `app/annotation/state/core_init.py` — `__init__` da ferramenta: resolve caminhos de saída, valida entradas, carrega modelo, constrói UI e inicia a primeira fonte.
- `app/annotation/state/runtime_state.py` — inicializa todas as variáveis de estado runtime (detecções, zoom, undo stack, tracking state, etc.).
- `app/annotation/state/class_config.py` — re-exporta `ClassConfigMixin` composto por `ClassServiceMixin` + `ClassPanelWidgetMixin`.

---

### Domínio (`core/`)

Lógica pura de negócio — sem UI, sem I/O, sem dependência de Tkinter ou arquivo.

- `app/annotation/core/services/class_service.py` — gerenciamento de categorias: registro, remapeamento de IDs, reordenação, remoção, cor, atalhos de teclado.
- `app/annotation/core/augmentation/augmentation_types.py` — catálogo canônico e dataclasses de configuração de data augmentation.
- `app/annotation/core/augmentation/augmentation_service.py` — transformações puras de augmentation sobre imagem BGR e bboxes YOLO normalizadas.
- `app/annotation/core/export/export_types.py` — dataclasses compartilhadas de configuração de exportação.
- `app/annotation/core/export/split_service.py` — cálculo puro de split train/val/test.
- `app/annotation/core/export/yolo_label_service.py` — conversão pura COCO bbox → YOLO normalizado e formatação de labels.

---

### Infraestrutura (`infrastructure/`)

Implementações concretas de I/O: leitura/escrita de arquivos, chamadas a bibliotecas externas.

#### Persistência

- `app/annotation/infrastructure/persistence/coco_storage.py` — operações COCO em memória e disco: `store_annotations`, `write_annotations`, `build_coco_payload`, `delete_image_annotations`, índices de lookup por imagem, etc.
- `app/annotation/infrastructure/persistence/async_writer.py` — escritor em background do arquivo de estado; o autosave não bloqueia a UI.
- `app/annotation/infrastructure/persistence/export_actions.py` — ações de exportação disparadas pela UI: salvar `.coco.json`, salvar `.yaml`, exportar dataset completo.

#### Exportação

- `app/annotation/infrastructure/export/coco_exporter.py` — conversão e escrita COCO.
- `app/annotation/infrastructure/export/yolo_exporter.py` — escrita YOLO, cópia de imagens, labels e cópias aumentadas.

---

### Aplicação (`application/`)

Casos de uso que orquestram domínio + infraestrutura sem conhecer a UI diretamente.

- `app/annotation/application/lifecycle.py` — `autosave_current_frame`, `finish_processing`, `run` (loop Tkinter) e encerramento seguro (evita `Tcl_AsyncDelete` na saída).

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

#### Exportação

- `app/annotation/presentation/export/export_screen.py` — tela interna de exportação com destino, formato, split e data augmentation (compartilhada por detecção, OBB e keypoint).
- `app/annotation/presentation/export/preview_dialog.py` — modal de preview antes/depois para uma augmentation específica.

---

### Fontes de mídia (`sources/`)

- `app/annotation/sources/source_discovery.py` — descobre vídeos, pastas de imagens e listas de imagens.
- `app/annotation/sources/source_loading.py` — carrega fontes, registra handlers de sinal, navega entre fontes.
- `app/annotation/sources/source_helpers.py` — reset de estado, retomada de posição, leitura do primeiro frame.

---

### ROI e homografia (`roi/`)

- `app/annotation/roi/roi_state.py` — captura de 4 pontos, cálculo de homografia, salvamento em `saved_data_states/homography.json`.
- `app/annotation/roi/roi_projection.py` — `warp_frame`, `project_bbox`, `is_inside_roi`.

---

### Detecção e rastreamento (`detection/`)

- `app/annotation/detection/frame_pipeline.py` — processa cada frame: roda modelo, aplica tracking, filtra por ROI, monta objetos `Detection`.
- `app/annotation/detection/frame_model_helpers.py` — inferência YOLO, NMS de ensemble multi-modelo.
- `app/annotation/detection/tracking_ids.py` — geração e matching de `track_id` (ID global, ID manual, histórico recente).
- `app/annotation/detection/selection_edit.py` — undo/redo (stack de snapshots), seleção de detecção, edição de ID e classe.
- `app/annotation/detection/review_nav.py` — `ReviewNavMixin`, composto por:
  - `review_cache.py` — cache LRU dos frames salvos (`MAX_SAVED_FRAME_CACHE`).
  - `review_annotations.py` — reconstrução de `Detection` a partir do COCO salvo.
  - `review_navigation.py` — entrada/saída do modo revisão e navegação entre frames salvos.
- `app/annotation/detection/workflow_actions.py` — `on_accept`, `on_reject`, `on_quit`, `on_delete_image`, memória de tracks manuais.
- `app/annotation/detection/persistence.py` — re-exporta `PersistenceMixin` composto por `CocoStorageMixin` + `ExportActionsMixin` + `LifecycleMixin`.

---

### Atalhos de teclado (`keybinds/`)

- `app/annotation/keybinds/actions.py` — `ACTION_REGISTRY`: ações remapeáveis com grupo, handler, modos suportados e teclas padrão por perfil. Novas ações entram aqui.
- `app/annotation/keybinds/keybind_map.py` — `KeybindMap`: perfil (ação → tecla) com detecção de conflito.
- `app/annotation/keybinds/keybind_repository.py` — perfis padrão (`arrows`, `wasd`) e persistência em `.local/keybinds.json`.
- `app/annotation/keybinds/keybind_service.py` — aplica um perfil à janela Tkinter (bind/unbind).
- `app/annotation/keybinds/keybind_mixin.py` — integra o serviço aos mixins de UI.
- `app/annotation/keybinds/keybind_editor.py` — editor visual de atalhos (captura de tecla, perfis, restaurar padrões).

---

### UI — controles e renderização (`ui/`)

- `app/annotation/ui/ui_layout.py` — re-exporta `UILayoutMixin` composto pelos cinco painéis de `presentation/panels/`.
- `app/annotation/ui/ui_controls.py` — bind de atalhos de teclado, mapeamento de teclas, estado dos botões.
- `app/annotation/ui/display_canvas.py` — renderização do frame no canvas, zoom, pan, coordenadas imagem↔canvas.
- `app/annotation/ui/display_overlays.py` — desenho de bounding boxes e overlay de ROI no canvas.
- `app/annotation/ui/display_status.py` — atualização dos blocos de status, label de imagem, botão "Ver em folder".
- `app/annotation/ui/mouse_events.py` — eventos de mouse: desenhar caixa, selecionar, remover, pan, zoom.
- `app/annotation/ui/mode_toggles.py` — alternância exclusiva de modos (anotação, remoção, seleção, editar ID, pan).
- `app/annotation/ui/rotation_utils.py` — rotação visual de 90° do canvas (não altera imagem nem coordenadas salvas).

---

### Composição principal

- `app/annotation/tool.py` — define `AnnotationTool` compondo todos os mixins por camada, com comentários que indicam a origem de cada capacidade.

---

## Modo OBB (`app/annotation_obb/`)

Mesma organização de `app/annotation/`; só contém o que difere para caixas rotacionadas.

- `tool.py` — `OBBAnnotationTool`.
- `geometry/obb_geometry.py` — `OBBDetection` e geometria de caixas orientadas (cantos, ângulo, conversões).
- `state/runtime_state.py` — estado runtime específico de OBB.
- `sources/source_helpers.py` — reset de estado por fonte.
- `detection/` — pipeline de frame, inferência OBB, workflow (aceitar/rejeitar), revisão e seleção/edição.
- `infrastructure/persistence/obb_coco_storage.py` — COCO OBB (`annotations_obb.coco.json`).
- `infrastructure/persistence/export_actions.py` — ações de exportação do modo.
- `infrastructure/export/yolo_obb_exporter.py` — exportação no formato YOLO OBB (`class x1 y1 ... x4 y4`).
- `ui/` — canvas, overlays, status, mouse (desenho/rotação de caixas), toggles e controles.

---

## Modo Keypoint (`app/annotation_keypoint/`)

- `tool.py` — `KeypointAnnotationTool`.
- `geometry/keypoint.py` — `KeypointInstance`: pontos ordenados, visibilidade COCO (0/1/2) e bbox derivada dos pontos visíveis.
- `state/runtime_state.py` — estado runtime (instância em construção, seleção, visibilidade pendente).
- `sources/source_helpers.py` — reset de estado por fonte.
- `detection/frame_pipeline.py` — processamento de frame e inferência de pose.
- `detection/workflow_actions.py` — aceitar/rejeitar/sair.
- `detection/review_nav.py` — revisão de frames salvos e reconstrução de instâncias.
- `detection/selection_edit.py` — hit-test (ponto antes de instância), mover pontos, undo, fechamento em modo livre.
- `infrastructure/persistence/coco_storage.py` — COCO Keypoints (`annotations_keypoints.coco.json`).
- `infrastructure/persistence/export_actions.py` — ações de exportação do modo.
- `infrastructure/export/coco_keypoints_exporter.py` — exportação COCO Keypoints e validação do payload (`keypoint_payload_errors`).
- `infrastructure/export/yolo_pose_exporter.py` — exportação YOLO Pose com `kpt_shape` no `data.yaml`.
- `core/augmentation/pose_augmentation.py` — augmentation que transforma também os keypoints (sobre o serviço de bbox).
- `ui/display_canvas.py` — rasteriza só o recorte visível, para o custo de zoom ficar proporcional ao canvas.
- `ui/display_overlays.py` — desenha keypoints como itens leves do canvas Tk (sem re-rasterizar a imagem).
- `ui/mouse_events.py` — colocação de pontos, visibilidade, `Esc` cancela a operação (não fecha o app).
- `ui/display_status.py`, `ui/mode_toggles.py`, `ui/ui_controls.py` — status, toggles e atalhos do modo.

---

## Modo Classificação (`app/classification/`)

- `tool.py` — wrapper de compatibilidade para `ClassificationTool`.
- `dataset.py` — operações de dataset: pastas por classe, cópia/movimentação de imagens, estado em `classification_state.json`.
- `tools/core.py` — composition root da ferramenta.
- `tools/state.py` — persistência do estado.
- `tools/ui.py` — layout Tkinter e atalhos.
- `tools/navigation.py` — navegação entre imagens e renderização no canvas.
- `tools/class_actions.py` — gerenciamento de classes e atribuição imagem → classe.
- `tools/dataset_actions.py` — ações de dataset (apagar imagem, exportar pastas).

---

## Núcleo compartilhado

- `app/core/session.py` — `AnnotationSessionConfig` (imutável) e `AnnotationTaskMode`.
- `app/core/output_state.py` — pastas de projeto/estado: criação (`create_new_output_dir`), listagem, retomada e detecção do arquivo de anotação.
- `app/core/startup_cache.py` — cache local (`.local/`) dos caminhos escolhidos no wizard.
- `app/models.py` — dataclasses `Detection` e `ByteTrackerArgs`.
- `app/geometry.py` — utilitários geométricos (`bbox_iou`, `clip_bbox`, `order_points`, etc.).
- `app/dataset_export.py` — fachada compatível para `export_detection_coco_json`, `export_yolo_dataset` e `export_yolo_no_split`.
- `app/config.py` — constantes e defaults de configuração.
- `app/sources/discovery.py` — descoberta de fontes independente de UI.
- `app/tracking/multiclass_byte_tracking.py` — `BYTETracker` independente por classe (sobre `tracker/`, vendorizado do ByteTrack).

---

## UI compartilhada (`app/ui/`)

- `theme/tokens.py` — design tokens (cores, fontes, espaçamentos, tamanhos) e `build_scaled_theme`/`install_scaled_theme`.
- `theme/palette.py` — paleta de cores das classes de anotação (`CLASS_COLORS`).
- `theme/__init__.py` — re-exporta tokens e paleta; `from app.ui.theme import COLORS` continua funcionando.
- `theme.py` — shim legado; o pacote `theme/` tem precedência no import, então este arquivo não é carregado.
- `components/` — widgets reutilizáveis: `badge`, `button` (com hover), `card`, `canvas`, `divider`, `entry`, `loading` (tela de carregamento sobreposta).
- `layout/scale.py` — fator de escala da UI a partir da altura do monitor e DPI.
- `layout/responsive_window.py` — helpers de janela responsiva.
- `layout/scrollable_frame.py` — frame vertical rolável.
- `startup/splash.py` — splash exibido enquanto dependências pesadas carregam em background.
- `startup/intro.py` — tela de boas-vindas antes do wizard.
- `startup/wizard.py` — wizard de configuração da sessão (modo, dataset, estado de saída, modelos e classes).
- `file_manager.py` — abre arquivos/pastas no gerenciador do sistema.

---

## Fora de `app/`

- `tracker/` — BYTETracker (Kalman filter, matching) de FoundationVision/ByteTrack.
- `utils/` — scripts CLI: conversão COCO → YOLO, merge de splits, tracking → detecção, augmentation de dataset, conserto de COCO Keypoints. `annotation_tool_bytetracked.py` é a ferramenta monolítica antiga, mantida só como referência.
- `build.sh` / `InoLabel.spec` — build com PyInstaller.

---

## Testes (`tests/`)

Rodar com `python -m pytest -q tests`.

| Área | Arquivos |
|------|----------|
| Sessão, wizard e estado | `test_session_config.py`, `test_session_installer.py`, `test_output_state.py`, `test_startup_cache.py` |
| Classes | `test_class_order.py`, `test_class_removal.py`, `test_model_class_mapping.py` |
| Persistência e exportação | `test_dataset_export.py`, `test_annotation_storage_perf.py`, `test_export_threading.py` |
| OBB | `test_obb_geometry.py`, `test_obb_tool_contract.py`, `test_yolo_obb_export.py` |
| Keypoint | `test_keypoint_*.py` (geometria, mouse, overlays, revisão, seleção, storage, descoberta de estado, consistência, exportação pose/YOLO Pose) — usam `_keypoint_harness.py` para testar mixins sem Tk |
| Classificação | `test_classification_dataset.py` |
| UI e tema | `test_components.py`, `test_theme.py`, `test_theme_compat.py`, `test_palette.py`, `test_scale.py`, `test_keybinds.py` |
| Startup e encerramento | `test_lazy_torch_import.py`, `test_shutdown.py` |

- `main_test.py` — script manual (não é teste unitário): processa 10 frames do primeiro vídeo em `videos/`.
