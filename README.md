# InoLabel

Ferramenta de anotação de imagens e vídeos desenvolvida pelo **Laboratório de Visão Computacional — Inovisão**.
Suporta quatro modos de trabalho: tracking, detecção padrão, detecção orientada (OBB) e classificação de imagens.

---

## Requisitos de ambiente

- Python 3.9+ via `conda`
- Tkinter (`sudo apt-get install python3-tk` no Ubuntu/Debian)
- Toolchain nativo (`build-essential`, `python3-dev`, `cmake`) — necessário para `lap`/`cython_bbox`
- (Opcional) CUDA para acelerar inferência YOLO na GPU

---

## Instalação

```bash
conda create -n anotador python=3.9
conda activate anotador
conda install -c conda-forge --file requirements.txt
```

---

## Como rodar

```bash
python main.py
```

O wizard de configuração abrirá pedindo:

1. **Modo** — escolha entre os quatro modos abaixo
2. **Dataset** — pasta, vídeo, imagem única ou lista `.txt`/`.lst`
3. **Estado de saída** — continuar saída anterior, usar como template ou criar novo
4. **Modelo e classes** — adicione um ou mais pesos YOLO `.pt` (opcional) e configure as classes da sessão

---

## Modos de anotação

| Modo | Descrição |
|------|-----------|
| **Tracking** | Mantém identidade dos objetos entre frames via BYTETracker por classe |
| **Detecção padrão** | Caixas independentes por frame, sem `track_id` |
| **Detecção orientada (OBB)** | Caixas rotacionadas com ângulo, exportáveis no formato YOLO OBB |
| **Classificação** | Copia imagens para subpastas por classe ao pressionar o atalho da classe |

O modelo YOLO é **opcional** em todos os modos — é possível anotar inteiramente de forma manual.

---

## Atalhos principais

Os atalhos são **totalmente remapeáveis** pelo editor visual (botão **Atalhos** na barra superior). Os valores abaixo são os padrões do perfil `arrows`.

| Tecla | Ação |
|-------|------|
| `Enter` | Validar / salvar frame atual |
| `Espaço` | Rejeitar / avançar frame |
| `→` / `←` | Navegar entre frames salvos (perfil `arrows`) |
| `D` / `A` | Navegar entre frames salvos (perfil `wasd`) |
| `K` | Liga/desliga anotação manual |
| `S` | Modo de seleção de anotação |
| `H` | Liga/desliga modo mover imagem (pan) |
| `R` | Redefinir ROI |
| `E` | Editar ID de tracking (apenas modo tracking) |
| `Ctrl+Z` | Desfazer última ação |
| `Ctrl+0` | Ajustar imagem na tela |
| `1–9` | Trocar classe ativa |
| `Scroll` | Zoom centrado no cursor |
| `Esc` | Sair |

### Editor de atalhos

Clique no botão **Atalhos: arrows** (topbar) para abrir o editor visual. Nele é possível:

- Remapear qualquer ação clicando no botão da tecla e pressionando a nova tecla
- Criar perfis personalizados ou alternar entre `arrows` e `wasd`
- Restaurar os padrões de fábrica por perfil
- Detectar conflitos em tempo real (aviso laranja, não bloqueante)

O perfil ativo é salvo em `.local/keybinds.json` e restaurado automaticamente na próxima sessão.

---

## Rotação visual da imagem

Os botões **↺ Girar** e **Girar ↻** na barra lateral rotacionam a exibição em 90° sem alterar a imagem salva nem as coordenadas das bounding boxes. A rotação é desfeita automaticamente ao avançar para o próximo frame. Atalhos de teclado podem ser atribuídos via editor de atalhos (grupo **Imagem**).

---

## Fluxo de ROI (Tracking / Detecção / OBB)

1. Ao abrir cada fonte, clique 4 pontos para definir o ROI (ordem livre; o código ordena automaticamente).
2. A homografia é calculada e `warpPerspective` é aplicado internamente.
3. A detecção ocorre na imagem retificada; as caixas são mapeadas de volta ao frame original.
4. Pressione `R` a qualquer momento para redefinir o ROI sem perder anotações já salvas.

---

## Exportação de dataset

Clique em **Exportar dataset** na barra lateral para abrir a tela de exportação. As opções disponíveis são:

| Opção | Descrição |
|-------|-----------|
| **Destino / Nome da pasta** | Caminho e nome da pasta de saída |
| **YOLO** | Exporta imagens + labels `.txt` e `data.yaml` |
| **COCO (.json)** | Exporta `annotations.coco.json` + pasta `images/` com as imagens |
| **Split train/val/test** | Divide as imagens em proporções configuráveis |
| **Data augmentation** | Gera cópias aumentadas por imagem (flip, brilho, ruído, etc.) |

A exportação roda em **background** — a interface permanece responsiva. Uma barra de progresso exibe o avanço imagem por imagem; ao concluir, ela some automaticamente.

---

## Saídas geradas

```
outputs/<tarefa>_<data>/
├── images/                         # frames salvos (originais ou retificados)
├── annotations.coco.json           # COCO com track_id (tracking) ou bbox simples
├── annotations_obb.coco.json       # COCO OBB (modo OBB)
├── annotations_detection.coco.json # COCO detecção padrão exportado pelo botão
├── yolo_dataset/                   # dataset YOLO exportado pelo botão
│   ├── data.yaml
│   └── images/ labels/ {train,val,test}/
└── homography.json                 # homografias por fonte (tracking/detecção)
```

Exportação manual via botão cria uma pasta separada (nunca sobrescreve `outputs/`):

```
<destino>/<nome>/
├── annotations.coco.json    # formato COCO
├── images/                  # imagens (cópia)
└── (ou estrutura YOLO acima)
```

---

## Utilitários

### Converter COCO → YOLO

```bash
python utils/convert_coco_to_yolo_dataset.py outputs/.../annotations.coco.json \
    --image-root outputs/.../images \
    --output-root outputs/.../yolo_dataset \
    --train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1
```

### Consolidar splits YOLO em train único

```bash
python utils/merge_yolo_splits.py outputs/.../yolo_dataset \
    --output-root outputs/.../yolo_dataset_train_only
```

### Converter anotações de tracking → detecção

```bash
python utils/convert_coco_tracking_to_detection.py outputs/.../annotations.coco.json
```

---

## Configurações em `app/config.py`

| Variável | Descrição |
|----------|-----------|
| `CONF_THRESHOLD` | Limiar de confiança do YOLO (padrão `0.40`) |
| `SAVE_RECTIFIED_FRAMES` | `True` salva frames com warpPerspective; `False` salva originais |
| `MANUAL_IOU_THRESHOLD` | IoU mínimo para fundir anotação manual com detecção existente |

Os caminhos de dataset, modelo e saída são configurados no wizard — os valores em `config.py` servem apenas como sugestão inicial.

---

## Resolução de problemas

| Problema | Solução |
|----------|---------|
| Tkinter não abre no WSL | Configure um X server e a variável `DISPLAY`, ou rode em ambiente gráfico nativo |
| Tkinter ausente no Linux | `sudo apt-get install python3-tk` |
| `lap`/`cython_bbox` falhando | Instale `build-essential python3-dev cmake` e tente novamente |
| Logo não aparece na tela inicial | Verifique se `assets/inovisao.png` existe e se `Pillow` está instalado |
| Atalhos não respondem após remapear | Verifique conflitos no editor de atalhos (aviso laranja) |

---

## Créditos

- BYTETracker retirado de [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack)
- Detecção e OBB via [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
