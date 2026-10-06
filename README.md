# InoLabel

Ferramenta de anotação de imagens desenvolvida pelo **Laboratório de Visão Computacional — Inovisão**.
Suporta cinco modos de trabalho: rastreamento (tracking), detecção padrão, detecção orientada (OBB),
keypoints (pose) e classificação de imagens.

O app roda na sua máquina: um servidor local (FastAPI) serve a interface (React), que abre no navegador
em `http://127.0.0.1:8765`. Nenhuma imagem sai do computador.

---

## Instalação — Linux (Ubuntu/Debian)

### 1. Dependências do sistema

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip \
    build-essential python3-dev cmake \
    zenity git
```

> `build-essential`, `python3-dev` e `cmake` são necessários para compilar `lap` e `cython-bbox`.
> `zenity` (GNOME) ou `kdialog` (KDE) abrem o seletor de pastas do sistema.

Para construir a interface também é preciso o **Node.js 18 ou mais novo** (recomendado 20), por exemplo
pelo [nodejs.org](https://nodejs.org/) ou pelo `nvm`.

### 2. Instalar Miniconda (recomendado)

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Feche e reabra o terminal após a instalação
```

### 3. Criar ambiente Python

```bash
conda create -n inolabel python=3.9 -y
conda activate inolabel
```

### 4. Instalar dependências do projeto

```bash
git clone <url-do-repositorio>
cd tracking-anotator
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

### 5. Rodar

```bash
python main.py
```

O navegador abre sozinho em `http://127.0.0.1:8765`.

---

## Instalação — Windows 11

### 1. Instalar Python 3.9

1. Acesse [python.org/downloads](https://www.python.org/downloads/) e baixe o Python **3.9.x** (64-bit)
2. No instalador, marque **"Add Python to PATH"** antes de clicar em Install
3. Após instalar, abra o **Prompt de Comando** e confirme:
   ```cmd
   python --version
   ```

### 2. Instalar Visual C++ Build Tools

Necessário para compilar `lap` e `cython-bbox`.

1. Acesse [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Baixe e execute o instalador
3. Selecione **"Desenvolvimento para desktop com C++"** e clique em Instalar
4. Aguarde (pode demorar alguns minutos)

### 3. Instalar CMake

1. Acesse [cmake.org/download](https://cmake.org/download/) e baixe o instalador `.msi`
2. Durante a instalação, selecione **"Add CMake to the system PATH"**

### 4. Instalar Node.js

1. Acesse [nodejs.org](https://nodejs.org/) e instale a versão **LTS** (20 ou mais nova)

### 5. Instalar Git (opcional, para clonar o repositório)

1. Acesse [git-scm.com](https://git-scm.com/) e instale com as opções padrão

### 6. Clonar e instalar o projeto

Abra o **Prompt de Comando** ou **PowerShell**:

```cmd
git clone <url-do-repositorio>
cd tracking-anotator
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### 7. Rodar

```cmd
python main.py
```

O navegador abre sozinho em `http://127.0.0.1:8765`.

---

## Gerar executável (build)

| Sistema | Comando | O que faz |
|---------|---------|-----------|
| Windows (PowerShell) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e `.\build.ps1` | Cria o ambiente conda `inolabel` se não existir, instala as dependências, roda `npm install` + `npm run build` e o PyInstaller |
| Linux / Git Bash | `bash build.sh` | Roda o PyInstaller; exige o frontend já construído (`npm run build` em `frontend/`) |

Saída:

```
APLICATIVO/InoLabel/InoLabel.exe           # build.ps1 (Windows)
dist/InoLabel-linux/InoLabel/InoLabel      # build.sh (Linux)
```

> O executável não inclui modelos nem dados — apenas o código da aplicação e a interface.
> **Tamanho esperado:** entre 1.5 GB e 3 GB (Ultralytics/PyTorch são pesados).

---

## Como usar

1. **Workspace** — na primeira vez, escolha a pasta onde os projetos ficam (como um "vault" do Obsidian).
   Os workspaces recentes aparecem nas próximas aberturas; **Projetos → Trocar workspace** muda de pasta.
2. **Modo** — escolha um dos cinco modos abaixo.
3. **Dados** — escolha a pasta do dataset (ou uma imagem) e dê um **nome ao projeto**. O projeto vira uma
   subpasta do workspace.
4. **Classes** — adicione as classes. No modo keypoint, defina também os pontos de cada classe.
5. **Anotar** — as alterações são salvas a cada operação. Para continuar depois, use **Projetos → Continuar**.
6. **Exportar** — `Ctrl+E` ou o botão de exportação na barra superior.

As páginas **Projetos** e **Histórico** listam os projetos do workspace (com a contagem de frames anotados);
**Atalhos** mostra todas as teclas.

---

## Modos de anotação

| Modo | Descrição |
|------|-----------|
| **Rastreamento** | Caixas com ID do objeto (`track_id`), mantido entre frames |
| **Detecção padrão** | Caixas independentes por frame, sem ID |
| **Detecção orientada (OBB)** | Caixas giradas, exportadas no formato YOLO OBB |
| **Keypoints** | Pontos nomeados por classe, clicados em ordem; exporta YOLO Pose e COCO Keypoints |
| **Classificação** | Cada imagem é copiada para a pasta da sua classe |

Em todos os modos de caixa: arraste para desenhar, clique numa caixa para selecioná-la e editar a classe no
painel lateral, `V` para mover, `Del` para apagar e `N` para marcar um frame **revisado sem objetos**
(ele entra na exportação como negativo).

### Rastreamento

- Cada caixa nova recebe o **próximo ID livre**; o painel **ID das próximas caixas** permite fixar um ID
  para seguir o mesmo objeto entre frames.
- O ID da caixa selecionada pode ser trocado no painel (**Novo ID** gera o próximo livre).

### Detecção orientada (OBB)

- Desenhe a caixa reta e gire pela **alça ○** acima dela (com `Shift`, de 15° em 15°), por `Q`/`E` (5°;
  com `Shift`, 1°) ou pelo campo **Ângulo** no painel.
- Com `V`, arraste a caixa girada para movê-la. A caixa nunca sai da imagem: perto da borda ela é
  empurrada para dentro, e uma rotação que não cabe é recusada.

### Keypoints (pose)

- No wizard, cada classe declara os nomes dos pontos **em ordem**, separados por vírgula (padrão:
  `top_left, top_right, bottom_right, bottom_left`). Sem pontos em todas as classes, o início fica bloqueado.
- Clique para marcar os pontos na ordem; um aviso no topo mostra o próximo. Ao marcar o último, a
  instância é salva.
- A **bounding box** é calculada a partir dos pontos marcados. Visibilidade (convenção COCO): `0` ausente,
  `1` oculto (círculo vazado), `2` visível (círculo cheio).
- Ao retomar um projeto, os pontos de cada classe vêm do próprio projeto. Mudar a quantidade de pontos de
  uma classe que já tem anotações é recusado.

| Tecla | Ação (modo keypoint) |
|-------|----------------------|
| Clique | Marcar o próximo ponto da classe (ferramenta `B`) |
| `X` | Pular o ponto (fica ausente) |
| `C` | Alternar visível/oculto — do ponto selecionado ou dos próximos pontos |
| `F` | Fechar a instância agora (pontos restantes ficam ausentes) |
| `Backspace` | Desfazer o último ponto da instância em andamento |
| `Esc` | Cancelar a instância em andamento |
| `V` + arrastar | Mover um ponto de uma instância salva |

### Classificação

- Clique na classe ou digite o **número** dela (a posição na lista). Até 9 classes a tecla já classifica;
  acima disso, digite o número e confirme com `Enter` (ele confirma sozinho quando não há ambiguidade).
- `/` busca a classe pelo nome, `Espaço` pula o frame e `Ctrl+Z` desfaz.
- Reclassificar **move** a imagem para a nova classe, sem duplicar.

### Pré-anotação por modelo

O wizard aceita pesos YOLO `.pt` e a confiança mínima, e a API tem a rota de inferência com rastreamento
(`POST /api/inference/tracking`). **A interface ainda não tem o botão para disparar a inferência** — por
enquanto a anotação é manual.

---

## Atalhos principais

| Tecla | Ação |
|-------|------|
| `→` / `D` | Próximo frame |
| `←` / `A` | Frame anterior |
| `B` | Ferramenta de caixa (ou de pontos, no modo keypoint) |
| `V` | Ferramenta de seleção / mover |
| Clique | Selecionar a caixa para editar classe / ID |
| `Del` | Remover a anotação selecionada |
| `Esc` | Desmarcar a anotação selecionada |
| `N` | Marcar frame revisado sem objetos (negativo) |
| `Q` / `E` | OBB: girar a caixa selecionada |
| `Ctrl+Z` | Desfazer (volta ao frame da operação, se preciso) |
| `Ctrl+E` | Abrir a exportação |
| `Ctrl+,` | Configurações da sessão |

A lista completa, por modo, está na página **Atalhos** do app.

---

## Exportação de dataset

| Opção | Descrição |
|-------|-----------|
| **Formatos** | YOLO e/ou COCO, juntos. Nos modos especiais: YOLO OBB e YOLO Pose / COCO Keypoints |
| **Organização do COCO** | Estilo **Roboflow** (padrão): `_annotations.coco.json` com as imagens na mesma pasta; ou pasta `images/` |
| **Destino / Nome** | Por padrão, a pasta `exports/` dentro do projeto |
| **Split train/val/test** | Divide as imagens em proporções configuráveis (somam 100%) |
| **Data augmentation** | Escolha das transformações e de 1 a 5 cópias por imagem. Só nas imagens de **treino** do YOLO — ligar o augmentation liga o split |
| **Pacote .zip** | Gera também `<nome>.zip`. As referências são conferidas antes (imagem ↔ label, `file_name` do COCO ↔ imagem) e o `data.yaml` vai sem caminho absoluto, para funcionar em outra máquina |

- As subpastas do dataset são preservadas; as categorias do COCO começam em `1`.
- Frames marcados como **revisados sem objetos** entram como negativos (imagem sem anotação).
- No modo keypoint, espelhar a imagem não troca os nomes dos pontos (um ponto "esquerdo" passa a ficar à
  direita); por isso o espelhamento fica fora do augmentation padrão nesse modo.

A exportação roda em segundo plano, com barra de progresso.

**Proteções do destino:**

- A exportação só apaga e recria pastas criadas por ela mesma (marcadas com o arquivo oculto `.inolabel_export`) ou vazias.
- Se o nome escolhido já existe e não é uma exportação do InoLabel, a saída vai para `<nome>_<data>` e a pasta existente não é tocada.
- São recusados como destino: a pasta do projeto e qualquer pasta acima dela, o dataset de origem (dentro, igual ou acima), a pasta pessoal e a raiz do disco, além de nomes como `.` e `..`.

Para conferir um dataset exportado, use `utils/verificar_export.py` (veja Utilitários).

---

## Saídas geradas

```
<workspace>/
├── .inolabel/workspace.json                 # índice do workspace (reconstruído se sumir)
└── <projeto>/
    ├── .inolabel.json                       # manifesto: modo, dataset, classes, pontos, frame atual
    ├── saved_data_states/                   # estado do projeto (fonte da verdade)
    │   ├── annotations.coco.json            # detecção / rastreamento (com track_id)
    │   ├── annotations_obb.coco.json        # modo OBB
    │   ├── annotations_keypoints.coco.json  # modo keypoint
    │   └── *.coco.json.bak                  # cópia do último estado, feita ao abrir a sessão
    ├── labels/                              # espelho .txt no formato YOLO do modo
    ├── classification_state.json            # modo classificação (+ uma pasta por classe)
    └── exports/                             # destino padrão da exportação
```

O estado COCO segue o formato da versão 1.0.0 (categorias a partir de 1, `bbox` em pixels, `file_name`
relativo ao dataset) e é a base para os scripts de treino.

---

## Utilitários

### Conferir um dataset exportado

Confere um export COCO ou YOLO (incluindo YOLO Pose e COCO Keypoints): imagens × anotações, ids, caixas
fora da imagem, categorias e pontos. A saída é só agregada, sem nomes de arquivo.

```bash
python utils/verificar_export.py <pasta exportada>
```

### Converter COCO → YOLO

```bash
python utils/convert_coco_to_yolo_dataset.py <projeto>/saved_data_states/annotations.coco.json \
    --image-root <pasta das imagens> \
    --output-root <projeto>/yolo_dataset \
    --train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1
```

### Consolidar splits YOLO em train único

```bash
python utils/merge_yolo_splits.py <projeto>/yolo_dataset \
    --output-root <projeto>/yolo_dataset_train_only
```

### Converter anotações de tracking → detecção

```bash
python utils/convert_coco_tracking_to_detection.py <projeto>/saved_data_states/annotations.coco.json
```

### Consertar COCO Keypoints antigo

`utils/fix_keypoint_coco.py` repara um COCO Keypoints inconsistente: preenche `categories[].keypoints`,
remove ponto de fechamento duplicado e recalcula `bbox`/`num_keypoints`. Por **padrão**, instâncias de 4
pontos são ordenadas em **TL → TR → BR → BL**; use `--no-sort-corners` para preservar a ordem original.

```bash
python utils/fix_keypoint_coco.py <projeto>/saved_data_states/annotations_keypoints.coco.json
```

### Baixar candidatas do Open Images para revisão

Baixa selfies com acessório (um rosto grande com a classe encostando nele) para `openimages_candidates/<classe>/`, sem tocar no dataset. Revise, apague o que não servir e mova as aprovadas para o dataset. O `candidates.csv` de cada pasta guarda a licença (CC BY 2.0: mantenha a atribuição), o autor e as caixas originais.

```bash
python utils/fetch_openimages.py --classes hat --limit 150
python utils/fetch_openimages.py --classes hat glasses --splits validation test train  # train: CSV de 2,2 GB lido em streaming
```

O Open Images não tem classe de máscara.

> **LGPD:** este utilitário baixa fotos de rosto de pessoas reais. A licença CC BY 2.0 cobre direitos autorais, não a proteção de dados pessoais. Antes de usar, registre a finalidade, a base legal e o prazo de retenção do material; mantenha `openimages_candidates/` fora do git (já está no `.gitignore`) e apague as candidatas descartadas. O utilitário não faz parte do executável distribuído.

### Data augmentation de um dataset de saída

```bash
python utils/augment_output_dataset.py --annotations <projeto>/saved_data_states/annotations.coco.json \
    --images-dir <pasta das imagens> --rotate90
```

> `utils/annotation_tool_bytetracked.py` é a ferramenta monolítica antiga, **obsoleta**: tem bugs já corrigidos no app (ex.: recorte de caixas) e não deve ser usada para anotar.

---

## Privacidade e segurança

- **Tudo local:** o servidor escuta só em `127.0.0.1`; imagens e anotações não saem da máquina.
- **Logs sem nomes de arquivo:** mensagens no terminal identificam imagens por `image_id` ou por uma referência anônima (`<arquivo 3f2a91c0>`), nunca pelo nome — nomes de arquivo em datasets de pessoas podem conter dados pessoais. A interface continua mostrando o nome ao próprio usuário.
- **Dados fora do git:** não versione datasets, pastas de projeto nem exportações; mantenha-os fora do repositório.
- **Pesos de modelo:** arquivos `.pt` usam pickle e executam código ao serem carregados. Abra apenas pesos de origem confiável.
- **Estado ilegível:** se o `annotations*.coco.json` não puder ser lido, a sessão não abre e o arquivo não é alterado. Restaure o `.bak` ao lado dele (gerado ao abrir cada sessão) ou corrija o JSON.

---

## Configuração

O app web não usa mais os parâmetros do app Tkinter em `app/config.py`. Os caminhos podem ser trocados por
variáveis de ambiente:

| Variável | Padrão | Uso |
|----------|--------|-----|
| `INOLABEL_LOCAL_DIR` | `.local/` ao lado do app | Workspaces recentes e atalhos |
| `INOLABEL_OUTPUT_BASE` | `outputs/` ao lado do app | Pasta de saída quando nenhuma é informada |
| `INOLABEL_ASSETS_DIR` | `assets/` | Recursos estáticos |
| `INOLABEL_ENV=development` | — | `python main.py` com recarga automática do servidor |

---

## Desenvolvimento

O código é organizado por funcionalidade:

```
app/api/<funcionalidade>/     router.py (HTTP) → service.py (casos de uso) + schemas.py e módulos de domínio
                              annotations, classification, session, frames, export, inference,
                              workspace, projects, classes, modes, keybinds, browse
app/api/common/               schemas compartilhados e erros de regra de negócio (DomainError)
app/api/state.py              estado em memória da sessão
app/core/project_state/       estado do projeto em annotations.coco.json
app/annotation/               exportadores YOLO/COCO, split e augmentation
frontend/src/features/        annotate, export, wizard, projects, workspace, help
frontend/src/shared/          cliente da API, tipos, sessão, layout e componentes de UI
```

Rodar com recarga automática (backend + frontend):

```bash
INOLABEL_ENV=development python main.py      # API em 127.0.0.1:8765
cd frontend && npm run dev                   # interface em localhost:5173 (encaminha /api para a 8765)
```

Testes e verificação:

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
cd frontend && npx tsc --noEmit && npm run build
```

O CI (`.github/workflows/ci.yml`) roda os testes Python e a checagem de tipos + build do frontend em todo
push e pull request para a `main`.

---

## Resolução de problemas

| Problema | Solução |
|----------|---------|
| Página em branco ou "Not Found" ao abrir | O frontend não foi construído: rode `npm install && npm run build` em `frontend/` |
| Seletor de pasta não abre no Linux | Instale `zenity` (GNOME) ou `kdialog` (KDE) |
| Porta 8765 em uso | Feche a outra instância do InoLabel (ou o processo que usa a porta) |
| `lap`/`cython_bbox` falhando no Linux | Instale `build-essential python3-dev cmake` e tente novamente |
| `lap`/`cython_bbox` falhando no Windows | Instale o Visual C++ Build Tools e CMake conforme descrito acima |
| Sessão não abre com erro do `annotations.coco.json` | Estado ilegível: restaure o `.bak` ao lado do arquivo |

---

## Créditos

- BYTETracker retirado de [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack)
- Detecção e OBB via [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
