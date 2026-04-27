# Estrutura de Codigo

## Entrada
- `main.py`: entrada simples da aplicacao.
- `app/runner.py`: abre o wizard inicial, cria a sessao e inicia a anotacao.

## Core
- `app/core/session.py`: contrato de sessao (`AnnotationSessionConfig`) e modo (`tracking` ou `detection`).

## Startup UI
- `app/ui/startup/wizard.py`: fluxo responsivo em 3 etapas:
  1. escolher tracking ou deteccao padrao;
  2. importar/validar dataset;
  3. escolher modelo auxiliar e classes.
- `app/ui/theme.py`: tokens centrais de cores, fontes, espacamentos e tamanhos.
- `app/ui/layout/scale.py`: escala visual baseada em altura do monitor e DPI.
- `app/ui/layout/responsive_window.py`: dimensionamento baseado no monitor.
- `app/ui/layout/scrollable_frame.py`: telas rolaveis para monitores menores.
- `app/startup_dialog.py`: compatibilidade, reexporta o wizard atual.

## Descoberta de Fontes
- `app/sources/discovery.py`: servico independente de UI para descobrir videos, imagens e listas.
- `app/annotation/sources/`: leitura de frames e ciclo das fontes durante a anotacao.

## Anotacao
- `app/annotation/tool.py`: composicao da ferramenta por mixins.
- `app/annotation/state/`: inicializacao, estado runtime e configuracao de classes.
- `app/annotation/ui/`: tela de anotacao, canvas, controles, status e eventos.
- `app/annotation/roi/`: ROI e homografia.
- `app/annotation/detection/`: pipeline de inferencia, workflow, revisao, edicao e persistencia.

## Tracking
- `app/tracking/multiclass_byte_tracking.py`: `BYTETracker` independente por classe para reduzir troca de identidade entre classes.
- Modo `tracking`: salva `track_id`.
- Modo `detection`: salva anotacoes COCO sem depender de `track_id`.

## Exportacao e Utilitarios
- `app/dataset_export.py`: exportacao COCO/YOLO.
- `utils/`: scripts auxiliares de conversao, merge e augment.
- `tracker/`: implementacao ByteTrack.

## Testes
- `tests/test_session_config.py`: sessao e descoberta de fontes.
- `tests/test_scale.py` e `tests/test_theme.py`: escala visual e tokens de tema.
- `tests/test_dataset_export.py`: exportacao, persistencia e workflow.
