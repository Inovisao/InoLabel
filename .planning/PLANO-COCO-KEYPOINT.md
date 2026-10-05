# Plano — `annotations.coco.json` como base do projeto e modo keypoint

Data: 2026-10-05 · Branch: `correcao-pos-1.0.0` · Estado: proposta, nada implementado.

Este documento segue o fluxo de "feature nova" do `AGENTS.md`: especificação, plano técnico e tarefas pequenas. São duas entregas, e a segunda depende da primeira.

- **Parte A:** o app volta a gravar e a ler o `annotations.coco.json` do projeto.
- **Parte B:** o modo keypoint é portado para o app novo (API + React).

---

## 1. Situação atual (verificada no código)

| Ponto | Como está hoje | Onde |
|---|---|---|
| O que é salvo | Um `.txt` YOLO por frame em `<saída>/labels/<stem>.txt`, a cada mutação | `app/api/routes/annotations.py` (`_autosave`) |
| O que é lido ao retomar | Só esses `.txt` | `_load_frame_from_txt` |
| `annotations.coco.json` | Não existe como estado; COCO só sai pela exportação | `app/api/routes/export.py` |
| Imagens | Não são copiadas; o app lê direto do dataset | `app/api/routes/frames.py` |
| Fontes | Só pastas de imagens ou um arquivo de imagem; vídeo não é suportado | `_load_frame_paths` |

Três perdas de dado que isso causa hoje:

1. **`track_id` não sobrevive a um reinício.** O `.txt` YOLO não tem campo para ele; ao recarregar, a anotação volta com `track_id` vazio e `source="file"`. No modo tracking, fechar e reabrir o projeto apaga as identidades.
2. **`source` e `score` também se perdem** pelo mesmo motivo.
3. **Colisão de nomes** — *corrigida em 2026-10-05, fora deste plano.* O `.txt` era nomeado só pelo `stem`, e `lote_a/img_001.jpg` e `lote_b/img_001.jpg` gravavam no mesmo `labels/img_001.txt`. O label agora acompanha a subpasta (`app/core/label_paths.py`).

O COCO resolve as duas primeiras, porque guarda `track_id`, `source`, `score` e o caminho relativo da imagem.

---

## 2. Parte A — `annotations.coco.json` como base

### 2.1 Objetivo

Todo projeto de detecção, tracking e OBB mantém um `annotations.coco.json` sempre atualizado, no mesmo lugar e no mesmo formato da versão 1.0.0, para que os scripts de treino existentes continuem funcionando sem alteração.

### 2.2 Contrato do arquivo (igual ao 1.0.0)

Caminho: `<saída>/saved_data_states/annotations.coco.json` (OBB: `annotations_obb.coco.json`).

```json
{
  "info": {
    "description": "...", "version": "1.0", "app_version": "2.0.0",
    "task_mode": "detection", "data_root": "/caminho/do/dataset"
  },
  "licenses": [],
  "categories": [{"id": 1, "name": "carro", "color": "#1560BD", "supercategory": "none"}],
  "images": [{"id": 1, "file_name": "lote_a/img_001.jpg", "width": 1920, "height": 1080}],
  "annotations": [{
    "id": 1, "image_id": 1, "category_id": 1,
    "bbox": [x, y, w, h], "area": 0.0, "iscrowd": 0, "segmentation": [],
    "score": 1.0, "source": "manual", "track_id": 7
  }],
  "annotation_state": {"last_active_file_name": "lote_a/img_001.jpg", "last_active_frame_index": 12}
}
```

Regras que precisam ser preservadas:

- **`category_id` começa em 1** no arquivo. A API usa índice a partir de 0 internamente; a conversão (`+1` ao gravar, `-1` ao ler) fica num único lugar.
- **`bbox` em pixels absolutos `[x, y, largura, altura]`**, recortada à imagem; caixa sem área não é gravada.
- **`file_name` é o caminho relativo ao dataset**, com `/`, nunca só o nome do arquivo. Isso elimina a colisão do item 3 acima.
- **`track_id` só aparece no modo tracking**; `score` e `source` sempre.
- **`image.id` e `annotation.id` são estáveis** entre gravações: um registro existente mantém o id ao ser atualizado.

### 2.3 Comportamento

- **Gravação:** a cada mutação (criar, apagar, limpar frame), junto com o `.txt`. A montagem do payload acontece na hora; a escrita em disco vai para uma thread de fundo, atômica (`.tmp` + `replace`) e ordenada, para não travar a interface em projetos grandes. Ao parar a sessão ou encerrar o app, a gravação pendente é concluída antes de sair.
- **Leitura ao retomar:** o COCO é a fonte principal. Se ele não existir (projeto criado antes desta mudança), o app lê os `.txt` como hoje e gera o COCO na primeira gravação.
- **O `.txt` continua existindo** como espelho, porque o `AGENTS.md` trata o autosave em `.txt` como padrão a não quebrar e a página de projetos conta os arquivos de `labels/`. Já é nomeado pelo caminho relativo (`labels/lote_a/img_001.txt`), com leitura retrocompatível do nome antigo.
- **Arquivo ilegível:** a sessão não abre e o arquivo não é alterado; a API devolve erro 422 com o caminho e a orientação de restaurar o `.bak`. Um `.bak` é feito ao abrir a sessão, antes da primeira gravação.
- **Frame validado sem objetos:** entra em `images` sem anotações (negativo intencional). Frame nunca visitado não entra.

### 2.4 Decisões que precisam do dono do projeto

| # | Pergunta | Recomendação |
|---|---|---|
| A1 | O treino lê as imagens de onde? Na 1.0.0 elas eram copiadas para `<saída>/images/<file_name>`; o app novo não copia. | Não copiar, gravar `info.data_root` e deixar o `file_name` relativo a ele. Se o treino depender de `<saída>/images/`, copiar passa a ser necessário. |
| A2 | Fonte da verdade: COCO (com `.txt` derivado) ou `.txt` (com COCO derivado)? | COCO. Só ele guarda `track_id`, `source`, `score` e, depois, keypoints. |
| A3 | Projetos da 1.0.0 devem abrir no app novo? | Sim, e sai quase de graça: o formato é o mesmo. Exige só o item A1 resolvido. |
| A4 | Vídeo como fonte volta nesta entrega? | Não. É uma feature separada; o contrato do COCO já comporta (`images[].video`). |

### 2.5 Plano técnico

Ordem pedida pelo `AGENTS.md` para mudança de API: schema, depois rota, depois frontend.

| Ordem | Arquivo | Mudança |
|---|---|---|
| 1 | `app/core/coco_state.py` (novo) | Funções puras: `build_payload(session, frame_paths, frame_dims, annotation_store, meta)` e `load_payload(...)`, com a conversão de ids e o recorte de bbox (reaproveita `clip_coco_bbox`). Sem FastAPI, testável isoladamente. |
| 2 | `app/core/coco_state_writer.py` (novo) | Escritor em thread de fundo com escrita atômica e número de sequência. A lógica já existe em `app/annotation/infrastructure/persistence/async_writer.py` (mixin Tkinter); extrair para uma classe sem herança. |
| 3 | `app/api/state.py` | Guardar por sessão: mapa `file_name → image_id`, próximo `image_id`, conjunto de frames validados. Função `reset` cobre os campos novos. |
| 4 | `app/api/schemas.py` | `Annotation` e `AnnotationUpsert` ganham `score: Optional[float]`. Sem mudança de rota. |
| 5 | `app/api/routes/annotations.py` | `_autosave` chama o escritor do COCO além do `.txt`; `.txt` passa a usar caminho relativo. |
| 6 | `app/api/routes/frames.py` | Carga inicial pelo COCO; `_lazy_load_from_disk` vira fallback para projetos sem COCO. |
| 7 | `app/api/routes/session.py` | Ao iniciar: ler o COCO (`read_annotation_state`, já existente em `state_file.py`), fazer o `.bak`, recusar arquivo ilegível com 422. Ao parar: concluir a gravação pendente. |
| 8 | `app/api/routes/export.py` | Montar o payload de exportação a partir de `coco_state.build_payload`, em vez da montagem própria. Um formato só no projeto. |
| 9 | `frontend/src/api/types.ts` | `Annotation.score?`. Rodar `tsc --noEmit`. |

### 2.6 Tarefas (uma por vez, cada uma com teste)

1. `coco_state.build_payload`: formato exato, ids a partir de 1, `file_name` relativo, recorte, caixa sem área descartada.
2. `coco_state.load_payload`: ida e volta sem perda de `track_id`, `source`, `score`; ids estáveis.
3. Escritor de fundo: atomicidade, ordem (snapshot antigo não sobrescreve novo), conclusão no encerramento.
4. Autosave grava o COCO junto com o `.txt` (o caminho relativo do `.txt` já está feito).
5. Retomada pelo COCO; fallback para `.txt`; teste de que `track_id` sobrevive a parar e reiniciar a sessão.
6. Arquivo ilegível: 422, arquivo intacto, `.bak` criado ao abrir.
7. Exportação usando o mesmo payload; testes de exportação existentes continuam passando.
8. Abrir um projeto no formato da 1.0.0 (fixture sintética) e conferir que nada se perde.

Critério de pronto: um script de treino que lia o arquivo da 1.0.0 lê o arquivo novo sem alteração (validado com o dono do projeto num dataset sem pessoas).

---

## 3. Parte B — modo keypoint

### 3.1 O que já existe e é reaproveitado

Quatro módulos sobreviveram à remoção do Tkinter, não dependem dele e têm 18 testes passando:

| Módulo | Papel |
|---|---|
| `app/annotation_keypoint/geometry/keypoint.py` | `KeypointInstance`, validação, bbox envolvente, ponto mais próximo do clique |
| `.../infrastructure/export/yolo_pose_exporter.py` | Labels YOLO Pose, `data.yaml` com `kpt_shape`, split, augmentation |
| `.../infrastructure/export/coco_keypoints_exporter.py` | COCO Keypoints e validação de consistência por classe |
| `.../core/augmentation/pose_augmentation.py` | Augmentation de pose |

Os demais arquivos de `app/annotation_keypoint/` (storage em mixin, navegação de revisão, seleção) são específicos do app antigo. Servem de especificação de comportamento, não de código a reaproveitar.

### 3.2 Especificação

- **Configuração:** cada classe declara a lista ordenada de nomes dos pontos (ex.: `top_left, top_right, bottom_right, bottom_left`) e, opcionalmente, o esqueleto (pares de índices). Sem pontos declarados, a sessão não inicia.
- **Anotar:** clique a clique, na ordem declarada. O canvas mostra qual é o próximo ponto e quantos faltam. Completar a lista fecha a instância. `Esc` descarta a instância em andamento; `Ctrl+Z` desfaz o último ponto.
- **Editar:** arrastar um ponto de uma instância existente; alternar a visibilidade (visível, oculto, ausente) com a tecla `C`; apagar a instância inteira.
- **Persistência:** no COCO da Parte A, no padrão COCO Keypoints: `categories[].keypoints`, `categories[].skeleton`, `annotations[].keypoints` (`[x, y, v, ...]`), `num_keypoints` e a `bbox` envolvente. Arquivo: `annotations_keypoints.coco.json`.
- **Exportação:** YOLO Pose e COCO Keypoints pelos exportadores existentes.
- **Fora do escopo desta entrega:** pré-anotação por modelo de pose (a rota de inferência só trata detecção e tracking).

Casos de borda a cobrir: ponto clicado fora da imagem (recusar), instância com todos os pontos ausentes (inválida), classes com quantidades diferentes de pontos (permitido entre classes, proibido dentro da mesma classe), troca de classe com instância em andamento (descartar com aviso).

### 3.3 Plano técnico

| Ordem | Camada | Arquivo | Mudança |
|---|---|---|---|
| 1 | Schema | `app/api/schemas.py` | `TaskMode.KEYPOINT`; `KeypointClassSpec {name, keypoints, skeleton}`; `SessionStartRequest.keypoint_classes`; `Annotation.keypoints: Optional[List[List[float]]]` |
| 2 | Estado | `app/api/state.py` | `SessionState.keypoint_specs` |
| 3 | Modos | `app/api/routes/modes.py` | Registrar `keypoint` |
| 4 | Sessão | `app/api/routes/session.py` | Validar que toda classe tem pontos; gravar as specs no `.inolabel.json` e no COCO |
| 5 | Anotações | `app/api/routes/annotations.py` | Aceitar `keypoints`; validar contagem contra a spec da classe; calcular `bbox` com `keypoints_bbox`; `.txt` espelho no formato YOLO Pose |
| 6 | Estado COCO | `app/core/coco_state.py` | Campos de keypoint em categorias e anotações |
| 7 | Exportação | `app/api/routes/export.py` | Desvio `mode == "keypoint"` chamando os dois exportadores de pose |
| 8 | Tipos | `frontend/src/api/types.ts` | `TaskMode`, `Annotation.keypoints`, `KeypointClassSpec` |
| 9 | Wizard | `frontend/src/components/wizard/StepMode.tsx`, `StepConfig.tsx` | Opção do modo; campo de pontos por classe |
| 10 | Canvas | `frontend/src/components/canvas/` | Extrair a interação de keypoint para um componente próprio (`KeypointLayer.tsx`) em vez de crescer o `AnnotationCanvas.tsx`, que já tem 436 linhas |
| 11 | Store | `frontend/src/stores/annotation.ts` | Instância em andamento, ponto selecionado |
| 12 | Barra de status e ajuda | `Statusbar.tsx`, `HelpPage.tsx` | Próximo ponto, atalhos |

Rotas novas ou alteradas: nenhuma rota nova. `POST /api/session/start` e `POST /api/annotations/{image_id}` aceitam campos adicionais.

### 3.4 Tarefas

1. Schemas e validação da sessão (testes de contrato da API).
2. Anotação com keypoints: criar, validar contagem, bbox derivada, ida e volta no COCO.
3. Exportação YOLO Pose e COCO Keypoints pela API.
4. Tipos e wizard no frontend; `tsc --noEmit`.
5. Canvas: desenhar instâncias existentes (pontos, rótulos, esqueleto).
6. Canvas: criar instância clique a clique, com indicador do próximo ponto.
7. Canvas: arrastar ponto, alternar visibilidade, apagar.
8. Teste manual com dataset sem pessoas e exportação conferida num treino curto.

O frontend segue os tokens do design system (`var(--color-*)`), sem valores fixos.

---

## 4. Ordem geral e dependências

1. **Pré-requisito:** `npm install` e build do frontend funcionando (ainda não foi feito neste branch).
2. **Parte A**, tarefas 1 a 8. Entrega isolada e já útil: devolve o arquivo que o treino usa e corrige a perda de `track_id`.
3. **Parte B**, tarefas 1 a 8. Depende de A para a persistência.
4. Antes do merge no `main`: reverter o commit `664d7c1` neste branch (ver mensagem do commit).

## 5. Riscos

- **A1 em aberto** muda o desenho da Parte A (copiar ou não as imagens). Resolver antes de começar.
- **Dois formatos em disco** (COCO e `.txt`) podem divergir se uma gravação falhar no meio. Mitigação: o COCO manda; o `.txt` é regenerado a partir dele ao abrir a sessão.
- **Projetos grandes:** regravar o JSON inteiro a cada mutação custa tempo proporcional ao dataset (na 1.0.0, 292 ms com 2.000 imagens antes do escritor de fundo). Por isso a escrita é assíncrona desde a primeira tarefa.
- **Canvas de keypoint** é a parte com mais incerteza de esforço; por isso fica por último e dividida em três tarefas.
