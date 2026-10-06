# Plano de correção — rotação de caixas no modo OBB

Data: 2026-10-06 · Branch: `correcao-pos-1.0.0` · Estado: **implementado em 2026-10-06** (D1 = (c), D2 = 5°/1°, D3 fora). Testes: `tests/test_obb_edit.py`; testado no navegador com dataset sintético.

## Problema

No modo OBB a caixa nasce alinhada aos eixos (`angle = 0`) e não há como girá-la. O formato
(YOLO OBB com 4 cantos) e o exportador já suportam ângulo; o que falta é a interação e a
consistência dos dados ao editar.

## Causa raiz

| # | Onde | O que acontece |
|---|------|----------------|
| R1 | `frontend/src/components/canvas/AnnotationCanvas.tsx` | Não existe nenhuma forma de rotacionar: sem alça, sem atalho, sem campo de ângulo. O desenho só cria retângulo alinhado; o backend converte em `obb` com ângulo 0 (`_obb_from_bbox`). Na 1.0.0 (Tkinter) havia uma alça de rotação acima da caixa (`app/annotation_obb/ui/mouse_events.py`, `rotation_handle_image_pos`), que não foi portada. |
| R2 | `app/api/routes/annotations.py::update_annotation` (PATCH) | Ao receber `obb`, mantém os `points` antigos (que o canvas usa primeiro, então a caixa desenhada nem muda) e não recalcula `bbox`. Ao receber só `bbox` no modo OBB (o "mover" da ferramenta V), o `obb` não acompanha: a caixa salva no COCO/export fica no lugar antigo. |
| R3 | Canvas — seleção | O clique testa o retângulo envolvente (`bbox`), não o polígono girado: com caixas inclinadas próximas, seleciona a errada. |
| R4 | Canvas — mover | Só o `Rect` (modo detecção) é arrastável; o grupo OBB (`Line`) não. |
| R5 | `stores/annotation.ts` / `api/types.ts` | `AnnotationPatch` do frontend não tem `obb`, e o desfazer de "update" não guarda o `obb` anterior. |

## Especificação (o quê)

1. **Alça de rotação**: caixa OBB selecionada mostra uma alça circular acima do lado superior
   (como na 1.0.0). Arrastar gira em torno do centro; com **Shift**, encaixa de 15° em 15°.
2. **Atalhos**: com uma caixa OBB selecionada, **Q** gira −5° e **E** gira +5°;
   **Shift+Q/E** ±1° (ajuste fino). Q/E não conflitam com A/D (navegação).
3. **Campo de ângulo** no painel "Caixa selecionada" (só no modo OBB), em graus, editável.
4. **Mover**: com a ferramenta V, arrastar a caixa OBB move o centro mantendo o ângulo.
5. **Seleção** pelo polígono girado (ponto dentro do quadrilátero), menor área vence.
6. **Desfazer** (Ctrl+Z) volta ângulo e posição.
7. **Consistência no backend**: toda mudança de geometria no modo OBB grava os três juntos —
   `obb` (cx, cy, w, h, angle), `obb.points` recalculados e `bbox` = envelope dos cantos.
   Ângulo normalizado para (−180°, 180°].

### Casos de borda

- **Caixa girada saindo da imagem**: hoje o exportador YOLO OBB corta cada canto em [0, 1],
  o que deforma o retângulo. **Decisão D1 (abaixo).**
- **PATCH com `bbox` e `obb` juntos**: `obb` vence e `bbox` é recalculado (evita estado divergente).
- **Projetos antigos** com `points` gravados e ângulo divergente: ao carregar, `points` é a verdade
  (é o que foi exportado); `cx/cy/w/h/angle` são recalculados a partir dele (`_obb_from_points`).
- **Caixa muito pequena**: a alça fica a uma distância mínima fixa em pixels de tela, para não
  sobrepor a caixa.
- Modos detecção/rastreamento não mudam.

## Plano técnico (ordem)

### Tarefa 1 — backend: geometria consistente (rota; schema não muda)
- `app/api/routes/annotations.py`: função única `_normalize_obb(obb) -> (obb_com_points, bbox_envelope)`
  usada no `add_annotation` e no PATCH.
  - PATCH com `obb` → recalcula `points` e `bbox`.
  - PATCH só com `bbox` no modo OBB → translada o `obb` pelo deslocamento do centro (mantém ângulo e tamanho).
  - `obb` fora do modo OBB → 422 (como já é feito com `track_id`).
- `AnnotationPatch.obb` já existe em `app/api/schemas.py`.
- Testes (`tests/test_obb_edit.py`): PATCH de ângulo recalcula `points`/`bbox`; mover por `bbox`
  translada o `obb`; normalização do ângulo; `obb` em modo detecção → 422; ida e volta pelo
  `annotations_obb.coco.json` e linha do YOLO OBB exportado com os cantos girados.

### Tarefa 2 — frontend: tipos e store
- `api/types.ts`: `AnnotationPatch.obb?: OBBGeometry`.
- Novo `frontend/src/components/canvas/obbGeometry.ts` (funções puras): `obbCorners`, `pointInPolygon`,
  `rotateObb(obb, deltaDeg)`, `angleFromCenter`, `normalizeAngle`.
- `stores/annotation.ts`: `updateAnnotation` aceita `obb`; o desfazer guarda o `obb` anterior;
  `rotateSelected(deltaDeg)`.

### Tarefa 3 — frontend: canvas
- Hit-test pelo polígono (R3).
- Grupo OBB arrastável com a ferramenta V (R4), envia `obb` com novo centro.
- Alça de rotação + linha guia; durante o arraste a pré-visualização é local e o PATCH sai
  só no `dragend` (um PATCH por gesto, uma entrada no desfazer).

### Tarefa 4 — frontend: atalhos, painel e ajuda
- `useKeyboardShortcuts.ts`: Q/E e Shift+Q/E quando o modo é OBB e há seleção.
- `Sidebar.tsx` (painel "Caixa selecionada"): campo "Ângulo (°)".
- Dica do canvas e `ShortcutsPage.tsx` com os novos atalhos.

### Tarefa 5 — verificação
- `pytest` completo, `tsc --noEmit`, `npm run build`.
- Navegador (chrome-devtools, dataset sintético): desenhar → girar pela alça, por Q/E e pelo campo →
  mover → desfazer → reabrir a sessão (ângulo persiste) → exportar YOLO OBB e conferir com
  `utils/verificar_export.py`.

## Decisões pendentes

- **D1 — cantos fora da imagem no export YOLO OBB.** Opções:
  (a) manter o corte por canto (atual; deforma a caixa);
  (b) não cortar, deixar cantos fora de [0, 1] (Ultralytics aceita, mas alguns loaders reclamam);
  (c) impedir no editor que qualquer canto saia da imagem (gira/move só até a borda).
  **Recomendação: (c)** — o dado salvo já nasce válido e o export não precisa adivinhar.
- **D2 — passo do Q/E.** Recomendação: 5° (Shift = 1°). A alça cobre ajustes grandes.
- **D3 — desenhar já girado** (3 cliques: dois cantos de um lado + largura, estilo roLabelImg).
  Recomendação: fora deste plano; desenhar reto e girar resolve o caso e é o fluxo da 1.0.0.
