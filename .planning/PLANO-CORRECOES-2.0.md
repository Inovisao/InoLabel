# Plano de correções e implementação — rastreamento, classificação, projetos e exportação

Data: 2026-10-05 · Branch: `correcao-pos-1.0.0` · Estado: **implementado em 2026-10-06** (decisões D1–D6 aprovadas; Roboflow como layout COCO padrão). Suíte: 544 testes; testado no navegador com dataset sintético. Falta o teste do usuário no app real.

Complementa `PLANO-COCO-KEYPOINT.md`. A Parte A daquele plano (o `annotations.coco.json` como base do projeto) passa a ser a fundação de quase tudo aqui, porque é o único lugar que guarda `track_id` e o estado completo do projeto.

Cada item abaixo diz se a causa foi **confirmada** (testada nesta data) ou se ainda precisa ser **reproduzida** no navegador antes de corrigir, como pede o fluxo de bug do `AGENTS.md`.

---

## 1. Diagnóstico

### 1.1 Pasta `anotacoes_guavira/` criada dentro do repositório — confirmado

O campo "pasta de saída" do wizard é texto livre, com `output` como sugestão (`StepData.tsx`). O servidor faz `Path(req.output_path or "outputs").resolve()` (`session.py`), e um nome sem caminho é resolvido a partir da pasta onde o app foi aberto. Rodando `python main.py` na raiz do repositório, o projeto vai parar dentro do repositório. No executável empacotado, vai para a pasta do `.exe`. É o mesmo defeito que torna a página de projetos imprevisível (item 1.4).

### 1.2 Rastreamento: não dá para escolher nem trocar o ID — confirmado

| Camada | Situação |
|---|---|
| API | `POST /api/annotations/{id}` aceita e devolve `track_id` (testado). |
| Frontend | `addAnnotation` nunca envia `track_id` (`stores/annotation.ts`). Não existe campo, atalho nem menu para escolher o ID. |
| Edição | Não existe rota para alterar uma anotação existente: só criar e apagar. Trocar classe ou ID de uma caixa é impossível. |
| Seleção | Não existe ferramenta de seleção. Os botões "Mover / selecionar" e "Desfazer" da barra lateral são decorativos: não têm ação (`Sidebar.tsx`, `ToolButton`). |
| Persistência | O `.txt` YOLO não tem campo para `track_id`; ao reabrir o projeto, todo ID volta vazio. |

### 1.3 Classificação — parcialmente confirmado

| Ponto | Situação |
|---|---|
| API | Funciona: classificar copia a imagem para `<saída>/<classe>/` e grava `classification_state.json` (testado). |
| Clique na classe | Só marca a classe como selecionada (`setSelectedClass`); não classifica a imagem. |
| Teclas 1 a 9 | O código existe (`useKeyboardShortcuts.ts`) e parece correto na leitura. **A causa de não funcionar precisa ser reproduzida no navegador.** Hipóteses a checar, nesta ordem: foco preso num elemento que intercepta a tecla, `mode` nulo após recarregar a página, erro silencioso da rota que só aparece no `error` da store. |
| Mais de 9 classes | Não há atalho além de 9, e nada na tela indica qual tecla é de qual classe. |
| Revisão | Ao voltar a uma imagem já classificada, a tela não mostra a classe escolhida, e não dá para desfazer nem reclassificar. |

### 1.4 Projetos — confirmado

- **Saída em texto livre** (item 1.1): projetos caem em lugares diferentes conforme de onde o app foi aberto.
- **A página de projetos varre uma pasta guardada no `localStorage` do navegador**, com padrão `output` relativo. Projetos criados em outro lugar não aparecem, e trocar de navegador "perde" todos eles.
- **Duas implementações para o mesmo endereço:** `validation.py` e `session.py` registram `GET /api/session/projects`, com regras diferentes. Responde a de `validation.py`, registrada primeiro em `main.py`; a de `session.py` é código morto.
- **Retomar depende do `data_path` salvo**; se o dataset mudou de lugar, o card fica inativo, sem opção de apontar o novo local.

### 1.5 Exportação — confirmado

| # | Problema | Onde |
|---|---|---|
| E1 | Um formato por vez: o modal manda `formats: [format]`. | `ExportModal.tsx` |
| E2 | A opção `augmentation` é aceita pela API e ignorada; o código de augmentation existe e não é chamado. | `schemas.py`, `routes/export.py` |
| E3 | Frames sem objetos nunca são exportados (`if not ann_list: continue`). Não existe como marcar "esta imagem foi revisada e não tem nada", então o dataset sai sem negativos. | `routes/export.py` |
| E4 | `category_id` começa em 0 no COCO exportado; na 1.0.0 começava em 1. Código de treino que espera a convenção antiga erra uma classe. | `routes/export.py` |
| E5 | O destino começa vazio e não tem relação com o projeto. | `ExportModal.tsx` |
| E6 | Nomes repetidos viram `img_000_3.jpg` (sufixo = índice interno do frame), sem como rastrear de qual subpasta a imagem veio. | `routes/export.py` |
| E7 | O COCO exportado põe as imagens em `images/` ao lado do `_annotations.coco.json`; o padrão Roboflow, que usa esse mesmo nome de arquivo, põe as imagens na mesma pasta do JSON. | `coco_exporter.py` |
| E8 | O modal mostra formatos marcados como "em breve" que não existem. | `ExportModal.tsx` |

---

## 2. Frente 1 — Workspace de projetos (modelo Obsidian)

### 2.1 Como fica para o usuário

Como os vaults do Obsidian:

1. **Na primeira abertura**, o app pede uma pasta para guardar os projetos (o *workspace*). Mostra três opções: criar um workspace novo, abrir um existente, ou continuar um recente.
2. **Criar projeto** pede só o nome e o dataset. A pasta do projeto é criada dentro do workspace (`<workspace>/<nome-do-projeto>/`); não existe mais campo de pasta de saída.
3. **A página de projetos lista o workspace atual**, sem varredura por pasta digitada. Trocar de workspace é uma ação explícita, com a lista de recentes.
4. **Dataset que mudou de lugar:** o card mostra "dataset não encontrado" com um botão para apontar o novo caminho.

### 2.2 Estrutura em disco

```
<workspace>/
  .inolabel/
    workspace.json          ← índice: versão, nome, lista de projetos
  guavira_lote1/
    .inolabel.json          ← manifesto do projeto (já existe hoje; mantido)
    saved_data_states/
      annotations.coco.json ← estado completo (Parte A do outro plano)
    labels/…                ← espelho .txt
    exports/                ← destino padrão das exportações
```

- **`workspace.json`** guarda `version`, `name`, `created_at` e a lista de projetos (`id`, `folder`, `name`, `mode`, `created_at`, `last_opened_at`). É um índice: se ele se perder ou divergir, é reconstruído varrendo as subpastas que têm `.inolabel.json`.
- **`.inolabel.json`** continua sendo o manifesto do projeto, o que mantém compatível tudo o que já foi criado. Ganha `version`, `id` e `data_path` relativo quando o dataset estiver dentro do workspace.
- **A lista de workspaces recentes** fica no app, em `LOCAL_DIR/workspaces.json`, como o Obsidian guarda a lista de vaults. Nunca no `localStorage` do navegador.
- **Projetos antigos** (pastas com `.inolabel.json` fora de um workspace) entram por "Abrir pasta como workspace", que cria o `.inolabel/workspace.json` sem mexer nos projetos.

### 2.3 Plano técnico

| Ordem | Arquivo | Mudança |
|---|---|---|
| 1 | `app/core/workspace.py` (novo) | Funções puras: criar, abrir, reconstruir índice, registrar projeto, validar nome de pasta (sem `..`, `/`, nomes reservados do Windows). Escrita atômica. |
| 2 | `app/api/schemas.py` | `WorkspaceInfo`, `WorkspaceCreate`, `ProjectCreate {name, mode, data_path, classes, …}`; `SessionStartRequest` passa a receber `project_id` em vez de `output_path` (com `output_path` aceito por compatibilidade, mas sempre absoluto). |
| 3 | `app/api/routes/workspace.py` (novo) | `GET/POST /api/workspace` (atual, criar, abrir), `GET /api/workspace/recent`, `GET/POST /api/workspace/projects`, `PATCH /api/workspace/projects/{id}` (renomear, novo `data_path`). |
| 4 | `app/api/routes/session.py` | Iniciar sessão a partir de um projeto do workspace; recusar `output_path` relativo com 422. |
| 5 | Remover | As duas implementações de `GET /api/session/projects` (em `validation.py` e em `session.py`), substituídas pela rota do workspace. |
| 6 | Frontend | Tela inicial de workspace; wizard sem campo de saída; `ProjectsPage` e `HistoryPage` lendo do workspace; botão "Apontar dataset". |

Testes: criar e reabrir workspace; reconstruir índice apagado; nome de projeto inválido; dois projetos com o mesmo nome; projeto antigo importado sem alteração; `output_path` relativo recusado; caminho com espaço e acento (ex.: `guavira teste`).

---

## 3. Frente 2 — Rastreamento: seleção e edição de ID

### 3.1 Comportamento

- **Ferramenta de seleção** (tecla `V`): clicar numa caixa a seleciona e mostra um painel com classe, ID e origem (modelo ou manual).
- **Atribuir ID:** no painel, campo numérico com sugestão do próximo ID livre; atalho `I` foca o campo. Enter confirma.
- **Trocar classe da caixa selecionada:** clicar na classe na barra lateral ou usar a tecla da classe.
- **Ao desenhar uma caixa nova no modo rastreamento**, ela recebe o próximo ID livre, ou o ID "fixado" pelo usuário (para seguir o mesmo objeto frame a frame sem redigitar).
- **Propagar ID:** opção de aplicar o ID à caixa correspondente no próximo frame (maior IoU com a caixa atual).
- **Desfazer** (`Ctrl+Z`) para criar, apagar e editar.
- **Apagar caixa selecionada** com `Delete`.

### 3.2 Plano técnico

| Ordem | Camada | Mudança |
|---|---|---|
| 1 | Pré-requisito | Parte A do `PLANO-COCO-KEYPOINT.md`: sem o COCO como estado, o ID some ao reabrir. |
| 2 | Schema | `AnnotationPatch {category_id?, track_id?, bbox?, obb?}`. |
| 3 | Rota | `PATCH /api/annotations/{image_id}/{ann_id}`; valida classe e regras do modo (detecção não aceita `track_id`). `GET /api/annotations/next-track-id`. |
| 4 | Store | `selectedAnnotationId`, `pinnedTrackId`, `updateAnnotation`, pilha de desfazer por frame. |
| 5 | Canvas | Seleção por clique (caixa de menor área sob o cursor), destaque, arrastar alças para redimensionar. |
| 6 | Painel | `AnnotationPanel.tsx` (novo) com classe, ID, origem, apagar. |
| 7 | Sidebar | Ferramentas passam a funcionar de verdade, com estado ativo visível. |

Testes: `PATCH` válido e inválido por modo; ID persiste ao reabrir; próximo ID livre; desfazer; `tsc --noEmit`.

---

## 4. Frente 3 — Classificação

### 4.1 Comportamento

- **Primeiro passo: reproduzir no navegador** por que as teclas 1 a 9 não funcionam, com o console aberto, e corrigir a causa real.
- **Clicar numa classe classifica a imagem** e avança. A classe atual da imagem fica destacada.
- **Atalhos para qualquer quantidade de classes:**
  - `1`–`9` e `0` (décima classe) direto;
  - acima de 10: digitar o número da classe e confirmar com Enter (ex.: `1` `2` Enter = classe 12), com o número aparecendo na tela enquanto é digitado e expirando em 1,5 s;
  - campo de busca por nome (`/` foca), para listas longas.
- **Cada botão de classe mostra o seu atalho.**
- **Revisão:** voltar a uma imagem mostra a classe já escolhida; escolher outra reclassifica (move o arquivo entre as pastas, sem duplicar); `Ctrl+Z` desfaz a última classificação.
- **Pular** (`Espaço`) avança sem classificar.
- **Barra de progresso:** quantas imagens classificadas, por classe.

### 4.2 Plano técnico

| Ordem | Camada | Mudança |
|---|---|---|
| 1 | Reprodução | Teste manual guiado; depois, teste automatizado do hook de teclado (Vitest + Testing Library, a adicionar como dependência de desenvolvimento). |
| 2 | Rota | `GET /api/annotations/{image_id}/classification` (classe atual); reclassificar troca o arquivo de pasta e atualiza o estado; `DELETE` desfaz. |
| 3 | Hook | Atalhos `0`–`9`, número + Enter, `Espaço`, `Ctrl+Z`, `/`. |
| 4 | Sidebar | No modo classificação, a lista de classes vira o controle principal: atalho visível, contagem por classe, clique classifica. |

Testes: reclassificar não duplica arquivo; desfazer remove a cópia e o registro; 12 classes com atalho numérico; estado sobrevive a reabrir.

---

## 5. Frente 4 — Exportação

| # | Mudança | Decisão necessária |
|---|---|---|
| E1 | Marcar vários formatos de uma vez; cada um vai para uma subpasta (`yolo/`, `coco/`). | — |
| E2 | Ligar a augmentation que já existe (`augmentation_service`), com as opções no modal, só no split de treino. | — |
| E3 | Permitir marcar imagem como "revisada, sem objetos" (tecla `N`); essas entram no dataset como negativos. Exportação ganha opção "incluir negativos". | Incluir negativos por padrão? |
| E4 | `category_id` do COCO volta a começar em 1, como na 1.0.0. | **Confirmar com o código de treino.** |
| E5 | Destino padrão: `<projeto>/exports/`; nome padrão: `<projeto>_<data>`. | — |
| E6 | Manter a estrutura de subpastas do dataset dentro da exportação (`images/lote_a/img_000.jpg`) em vez de sufixos numéricos; gravar um `manifest.csv` com origem → nome exportado. | — |
| E7 | Opção de layout COCO: "imagens em `images/`" (atual) ou "padrão Roboflow" (imagens ao lado do JSON). | **Qual o seu treino usa?** |
| E8 | Remover do modal os formatos "em breve". | — |
| E9 | Resumo ao terminar: imagens, caixas e negativos por split e por classe, avisos de recorte. Reaproveita `utils/verificar_export.py` dentro da exportação. | — |

Testes: exportação múltipla; augmentation só em treino; negativos; ids a partir de 1; subpastas preservadas; o verificador passa em todas as combinações.

---

## 6. Ordem de execução

1. **Correção rápida, isolada:** recusar `output_path` relativo (item 1.1). Evita novos projetos dentro do repositório já agora.
2. **Reproduzir os bugs de tela** (teclas da classificação), com você rodando o app e eu acompanhando os erros.
3. **Parte A do `PLANO-COCO-KEYPOINT.md`:** COCO como estado do projeto.
4. **Frente 1:** workspace de projetos.
5. **Frente 2:** seleção e edição de ID (depende de 3).
6. **Frente 3:** classificação.
7. **Frente 4:** exportação. E4 e E7 podem ser feitos antes, assim que as decisões chegarem, porque são pequenos.
8. **Modo keypoint** (Parte B do outro plano), por último.

Cada frente termina com `pytest`, `tsc --noEmit`, `npm run build` e um teste manual guiado.

## 7. Decisões pendentes, consolidadas

| # | Pergunta | Recomendação |
|---|---|---|
| D1 | O treino lê as imagens de onde (pasta do projeto ou dataset original)? | Do pacote exportado. |
| D2 | O treino espera imagens ao lado do JSON (Roboflow) ou em `images/`? | Oferecer os dois; padrão conforme a resposta. |
| D3 | `category_id` do COCO a partir de 0 ou de 1? | 1, como na 1.0.0 e no padrão COCO. |
| D4 | Negativos entram na exportação por padrão? | Sim, quando marcados explicitamente. |
| D5 | Um workspace por máquina ou vários, como o Obsidian? | Vários, com lista de recentes. |
| D6 | O que fazer com a pasta `anotacoes_guavira/` já criada no repositório? | Mover para o workspace quando ele existir; até lá, ignorar no `.gitignore`. |
