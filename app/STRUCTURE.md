# Estrutura de Codigo

## Entry point
- `main.py`: entrada simples da aplicacao.
- `app/runner.py`: bootstrap, tratamento de erro e encerramento.

## Nucleo de anotacao (modularizado por area)
- `app/annotation/tool.py`: composicao final da classe `AnnotationTool` via mixins.
- `app/annotation/core_init.py`: inicializacao principal.
- `app/annotation/runtime_state.py`: estado de execucao.
- `app/annotation/ui_layout.py`: construcao de layout/botoes.
- `app/annotation/ui_controls.py`: atalhos e estados de botoes.
- `app/annotation/source_discovery.py`: descoberta e leitura de fontes.
- `app/annotation/source_loading.py` + `source_helpers.py`: ciclo de carregamento da fonte.
- `app/annotation/roi_state.py` + `roi_projection.py`: ROI e homografia.
- `app/annotation/display_canvas.py` + `display_overlays.py` + `display_status.py`: renderizacao e status.
- `app/annotation/mouse_events.py` + `mode_toggles.py`: eventos do mouse e modos da UI.
- `app/annotation/frame_pipeline.py` + `frame_model_helpers.py`: pipeline de frame e inferencia.
- `app/annotation/tracking_ids.py`: gerenciamento de IDs.
- `app/annotation/workflow_actions.py`: acoes principais (aceitar/rejeitar/sair).
- `app/annotation/review_nav.py`: navegacao e revisao de frames salvos.
- `app/annotation/selection_edit.py`: selecao e edicao de track_id.
- `app/annotation/persistence.py`: persistencia de anotacoes e encerramento.
- `app/annotation/shared.py`: dependencias compartilhadas entre mixins.

## Compatibilidade
- `app/annotation_tool.py`: reexporta `AnnotationTool` para manter imports antigos.

## Configuracoes e utilitarios
- `app/config.py`: constantes, paths e flags.
- `app/models.py`: dataclasses (`Detection`, `ByteTrackerArgs`).
- `app/geometry.py`: utilitarios geometricos e de bbox.
