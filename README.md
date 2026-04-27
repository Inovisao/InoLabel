# Ferramenta de Anotacao com ROI, Homografia e Tracking (YOLO)

Interface Tkinter para validar e anotar deteccoes de imagens ou videos. O fluxo inicial permite escolher entre tracking e deteccao padrao, importar o dataset, selecionar o modelo auxiliar e configurar classes antes de abrir a tela de anotacao.

Bytetracker retirado de: https://github.com/FoundationVision/ByteTrack

## Requisitos de ambiente
- Python 3.9+ via `conda`.
- Tkinter instalado (Ubuntu/Debian: `sudo apt-get install python3-tk`).
- Toolchain para pacotes nativos (`build-essential`, `python3-dev`, `cmake`) — necessario para `lap`/`cython_bbox`.
- (Opcional) CUDA instalado caso queira acelerar o YOLO na GPU.
- Peso YOLOv11 `yolo11l.pt` na raiz do projeto (baixe da Ultralytics).

## Instalacao rapida
```bash
conda create -n tracking-anotator python=3.9
conda activate tracking-anotator
conda install -c conda-forge --file requirements.txt
```

Os caminhos de dataset e modelo podem ser escolhidos na tela inicial. Os valores de `app/config.py` funcionam apenas como defaults.

## Funcionalidades principais
- Percorre todas as fontes validas selecionadas no wizard e processa uma por vez.
- Selecao de ROI por 4 cliques; calcula homografia (M e M_inv) e aplica warpPerspective.
- Detecta na imagem retificada, mapeia caixas de volta ao frame original e descarta deteccoes fora do ROI.
- Modo tracking com `BYTETracker` separado por classe para reduzir troca de identidade em cenarios multiclass.
- Modo deteccao padrao sem dependencia de `track_id`.
- Anotacao manual com `track_id` em tracking, ou bbox simples em deteccao padrao.
- Salva COCO/MOT em `output_dataset/annotations.coco.json`, frames em `output_dataset/images/` e homografias em `output_dataset/homography.json`.
- Exporta COCO de deteccao por botao em `output_dataset/annotations_detection.coco.json`.
- Exporta dataset YOLO por botao em `output_dataset/yolo_dataset/`, com `data.yaml`, `images/{train,val,test}` e `labels/{train,val,test}`.
- Opcao de salvar frames retificados ou originais (`SAVE_RECTIFIED_FRAMES` em `app/config.py`).

## Estrutura esperada
```
tracking-anotator/
├── main.py
├── app/
└── utils/
```

## Como rodar
- Interface de anotacao:
```bash
python main.py
```
  1. Ao abrir cada video, clique 4 pontos para definir o ROI (ordem livre; o codigo ordena).  
  2. Antes da anotacao, escolha:
     - Tracking ou deteccao padrao
     - Dataset/fonte de dados
     - Modelo auxiliar e classes iniciais
  3. Interface apos ROI:
     - Enter: validar/salvar frame atual  
     - Espaco: pular frame  
     - K: liga/desliga modo anotacao manual  
     - Botao esquerdo + arrastar: desenhar caixa manual (quando anotacao ON)  
     - Botao "Remover anotacao": liga/desliga modo remocao (clique sobre uma caixa)  
     - R: redefinir ROI (nao altera anotacoes ja salvas do video atual)  
     - Botao `Salvar .coco.json`: gera um COCO de deteccao padrao
     - Botao `Salvar .yaml`: gera um dataset YOLO com `data.yaml`
  4. Ao fim de cada fonte, a proxima e aberta automaticamente.

Saidas geradas:
- `output_dataset/images/{video}_frame_00001.jpg` (originais ou retificados, conforme `SAVE_RECTIFIED_FRAMES`)
- `output_dataset/annotations.coco.json` (inclui `track_id` no modo tracking)
- `output_dataset/annotations_detection.coco.json` (COCO deteccao padrao)
- `output_dataset/yolo_dataset/data.yaml`
- `output_dataset/yolo_dataset/images/{train,val,test}/...`
- `output_dataset/yolo_dataset/labels/{train,val,test}/...`
- `output_dataset/homography.json` (lista de homografias por video)

## Conversao separada de COCO para YOLO
Use o script abaixo para ler um `.coco.json` e gerar a estrutura YOLO com `data.yaml`:

```bash
python utils/convert_coco_to_yolo_dataset.py output_dataset/annotations.coco.json
```

Opcoes uteis:
- `--image-root output_dataset/images`
- `--output-root output_dataset/yolo_dataset`
- `--train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1`

## Unir todos os splits YOLO em train
Use o script abaixo para consolidar um dataset YOLO existente em uma unica pasta `train`, util para validacao cruzada posterior sobre o conjunto completo:

```bash
python utils/merge_yolo_splits.py output_dataset/yolo_dataset
```

Opcao util:
- `--output-root output_dataset/yolo_dataset_train_only`

## Configuracoes uteis em `app/config.py`
- `SAVE_RECTIFIED_FRAMES`: False (salva originais) ou True (salva warpPerspective).
- `CONF_THRESHOLD`: limiar de confianca do YOLO.
- `TARGET_CLASSES`: classes iniciais sugeridas no wizard.

## Resolucao de problemas
- Tkinter nao abre no WSL: precisa de X server e variavel DISPLAY; ou rode em ambiente grafico nativo.
- Tkinter ausente no Linux: `sudo apt-get install python3-tk`.
- `lap`/`cython_bbox` falhando ao compilar: instale `build-essential python3-dev cmake` e tente novamente.
- Pesos nao encontrados: selecione o `.pt` no wizard ou ajuste `WEIGHTS_PATH` em `app/config.py`.
