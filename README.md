# InoLabel 🏷️

**Ferramenta desktop para anotar imagens e vídeos com bounding boxes, tracking, OBB e classificação.**

Crie datasets de alta qualidade para computer vision em minutos. Roda 100% localmente — seus dados nunca saem da sua máquina.

![Versão](https://img.shields.io/badge/versão-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-Inovisão-green)

---

## ⚡ Comece em 5 minutos

> **Primeira vez?** Leia a [Seção 1](#1-pré-requisitos-o-que-você-precisa) linha por linha. Levará 10 minutos e você não terá dúvidas.

### Resumido (se você já tem Git, Node.js e Miniconda)

```powershell
# Windows (PowerShell)
git clone https://github.com/Inovisao/InoLabel.git
cd InoLabel
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build.ps1
```

```bash
# Linux
git clone https://github.com/Inovisao/InoLabel.git
cd InoLabel
bash build.sh
```

Depois:
- **Windows**: `.\APLICATIVO\InoLabel\InoLabel.exe`
- **Linux**: `./dist/InoLabel-linux/InoLabel/InoLabel`

---

## 📚 Guia Completo

### 1. Pré-requisitos: O que você precisa

Antes de começar, instale **exatamente nesta ordem**:

#### **Windows 10/11**

| Ferramenta | Versão | Para quê? |
|-----------|--------|----------|
| **Git** | 2.40+ | Baixar o código do GitHub |
| **Node.js LTS** | 18+ | Gerar a interface (frontend) |
| **Miniconda** | Latest | Gerenciar ambiente Python |
| **Python** | 3.9, 3.10, 3.11 | Mecanismo de anotação |

**Instalação passo a passo:**

1. **Instale Git**
   - Acesse: https://git-scm.com/download/win
   - Clique em "Download for Windows"
   - Execute e clique "Next" em tudo (padrão é fine)
   - Após terminar, **feche o PowerShell** e abra um novo

2. **Instale Node.js**
   - Acesse: https://nodejs.org (botão verde "LTS")
   - Execute o instalador e clique "Next" em tudo
   - Após terminar, **feche o PowerShell** e abra um novo
   - Valide: `npm --version` (deve mostrar um número)

3. **Instale Miniconda**
   - Acesse: https://docs.conda.io/en/latest/miniconda.html
   - Escolha o arquivo **Windows 64-bit**
   - Durante a instalação:
     - ✅ Marque **"Add Miniconda3 to my PATH"**
   - Após terminar, **feche o PowerShell** e abra um novo
   - Valide: `conda --version` (deve mostrar um número)

#### **Linux (Ubuntu / Debian)**

```bash
# Atualize os pacotes
sudo apt-get update

# Instale Git, Node.js, ferramentas de compilação e OpenGL
sudo apt-get install -y git nodejs npm build-essential python3-dev cmake libgl1

# Instale Miniconda
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
bash miniconda.sh -b -p $HOME/miniconda3
source $HOME/miniconda3/etc/profile.d/conda.sh
conda init

# Feche e abra o terminal
# Valide: conda --version
```

---

### 2. Clone o Repositório (apenas uma vez)

Escolha uma pasta onde guardar seus projetos. Aqui usaremos `C:\Dev` no Windows ou `~/projects` no Linux.

**Windows (PowerShell):**
```powershell
cd C:\Dev  # Ou qualquer pasta de sua escolha
git clone https://github.com/Inovisao/InoLabel.git
cd InoLabel
```

**Linux:**
```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/Inovisao/InoLabel.git
cd InoLabel
```

---

### 3. Construir o Executável (5 a 15 minutos)

#### **Windows**

```powershell
# Certifique-se de estar na pasta do projeto
cd C:\Dev\InoLabel

# Abra um novo PowerShell e execute:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build.ps1
```

**O que o script faz:**
1. Verifica se você tem conda e Node instalados ✓
2. Cria um ambiente Python isolado chamado `inolabel`
3. Instala todas as dependências Python (~2 GB, leva 10-20 min)
4. Constrói a interface (frontend)
5. Gera o executável (etapa mais lenta)
6. Cria automaticamente as pastas `dataset/` e `outputs/`

**Não feche o PowerShell enquanto o build está rodando!**

Se deu erro, veja a [seção Troubleshooting](#troubleshooting).

#### **Linux**

```bash
cd ~/projects/InoLabel
bash build.sh
```

---

### 4. Onde fica o programa pronto

Após o build completar, o programa está em:

**Windows:**
```
APLICATIVO\InoLabel\
├── InoLabel.exe          ← Clique aqui para rodar!
├── _internal\            ← (ignorar)
├── dataset\              ← Coloque suas imagens aqui
├── outputs\              ← Anotações salvas aqui
└── model.pt              ← (opcional) seu modelo YOLO
```

**Linux:**
```
dist/InoLabel-linux/InoLabel/
├── InoLabel              ← Execute isto
├── _internal/            ← (ignorar)
├── dataset/              ← Coloque suas imagens aqui
├── outputs/              ← Anotações salvas aqui
└── model.pt              ← (opcional) seu modelo YOLO
```

---

### 5. Preparar seus Dados

#### **Colocar imagens/vídeos**

1. Reúna suas imagens ou vídeos
2. Coloque tudo na pasta `dataset/`

**Formatos aceitos:**
- **Imagens**: .jpg, .jpeg, .png, .bmp, .tif, .tiff
- **Vídeos**: .mp4, .avi, .mov, .mkv

Exemplo (Windows):
```
APLICATIVO\InoLabel\dataset\
├── gato_1.jpg
├── gato_2.jpg
├── cachorro_1.jpg
└── video.mp4
```

#### **(Opcional) Usar um modelo YOLO pré-treinado**

Se você tem um arquivo `model.pt` (de um treinamento anterior):

1. Copie `model.pt` para a pasta principal:
   - **Windows**: `APLICATIVO\InoLabel\model.pt`
   - **Linux**: `dist/InoLabel-linux/InoLabel/model.pt`

2. O programa detectará automaticamente

---

### 6. Rodar o Programa

#### **Windows**

```powershell
cd C:\Dev\InoLabel\APLICATIVO\InoLabel
.\InoLabel.exe
```

#### **Linux**

```bash
cd ~/projects/InoLabel/dist/InoLabel-linux/InoLabel
./InoLabel
```

**Espere 10-30 segundos.** O navegador deve abrir automaticamente em `http://127.0.0.1:8765`.

Se não abrir:
- Aguarde mais 30 segundos
- Digite manualmente no navegador: `http://127.0.0.1:8765`

---

### 7. Usar o InoLabel

#### **Na tela inicial (Setup Wizard)**

Você verá uma tela com 4 campos:

1. **Modo de anotação** — escolha um:
   - 🔲 **Detecção** — bounding boxes simples
   - 🟢 **Rastreamento** — identidade dos objetos entre frames
   - ◇ **OBB** — caixas rotacionadas (para objetos em ângulo)
   - 🏷️ **Classificação** — organizar imagens em categorias

2. **Pasta de dados** — caminho absoluto para suas imagens
   - Exemplo Windows: `C:\Dev\InoLabel\APLICATIVO\InoLabel\dataset`
   - Exemplo Linux: `/home/seu_usuario/projects/InoLabel/dist/InoLabel-linux/InoLabel/dataset`

3. **Pasta de saída** — onde salvar as anotações
   - Exemplo Windows: `C:\Dev\InoLabel\APLICATIVO\InoLabel\outputs`
   - Exemplo Linux: `/home/seu_usuario/projects/InoLabel/dist/InoLabel-linux/InoLabel/outputs`

4. **Modelo (opcional)** — deixe em branco ou aponte para `model.pt` se tiver

5. **Classes** — as categorias que você vai anotar
   - Exemplo: `gato`, `cachorro`, `pessoa`
   - Clique "+" para adicionar
   - Clique a cor para escolher a cor de cada classe

#### **Na tela de anotação**

- **Desenhar caixa** — clique e arraste na imagem
- **Selecionar caixa** — clique em uma caixa existente
- **Deletar caixa** — selecione e pressione `Delete` ou `X`
- **Próximo frame** — Espaço ou seta →
- **Frame anterior** — seta ←
- **Exportar dataset** — Menu → Exportar

---

### 8. Exportar seu Dataset

Após anotar os frames:

1. Clique em **"Exportar Dataset"** no menu lateral
2. Escolha o formato:
   - **YOLO** — padrão para treinar modelos
   - **COCO** — JSON estruturado
3. Escolha o **split** (divisão treino/validação):
   - 70% treino, 30% validação (padrão)
4. (Opcional) Aplique **data augmentation**
5. Clique **"Exportar"**

O dataset fica em `outputs/` pronto para usar com YOLOv8, YOLOv5, etc.

---

### 9. Parar o Programa

**Windows (no PowerShell onde está rodando):**
```powershell
Ctrl+C
```

**Linux (no terminal):**
```bash
Ctrl+C
```

Ou use o Gerenciador de Tarefas / Activity Monitor.

---

## 🛠️ Modo Desenvolvimento (sem build, rápido)

Se você quer testar rapidamente **sem gerar o executável** (útil para desenvolvedores):

```bash
# Na pasta do projeto
pip install -r requirements.txt

# Gere o frontend (primeira vez)
cd frontend && npm install && npm run build && cd ..

# Rode o servidor
python main.py
```

Acesse: `http://127.0.0.1:8765`

---

## ⚙️ Variáveis de Ambiente

Você pode customizar o local onde o programa salva os dados:

**Windows (PowerShell):**
```powershell
$env:INOLABEL_OUTPUT_BASE = "C:\meus_dados\anotacoes"
.\InoLabel.exe
```

**Linux:**
```bash
INOLABEL_OUTPUT_BASE="/home/seu_usuario/dados" ./InoLabel
```

---

## 🐛 Troubleshooting

### **Problema: "conda não é reconhecido"**
- Feche o PowerShell completamente
- Abra um **novo** PowerShell
- Se ainda não funcionar, abra "Anaconda Prompt" pelo Menu Iniciar

### **Problema: "Set-ExecutionPolicy não é reconhecido"**
- Você está no CMD, não no PowerShell
- Use: `powershell -ExecutionPolicy Bypass -File .\build.ps1`

### **Problema: "frontend\dist not found" durante build**
- Execute `npm run build` dentro da pasta `frontend\`
- Depois rode `build.ps1` novamente

### **Problema: "Windows protegeu seu computador"**
- Clique "Mais informações" → "Executar assim mesmo"
- (O executável não tem assinatura digital, é normal)

### **Problema: "Porta 8765 em uso"**
- Fecha outra instância do InoLabel
- Ou finalize o processo via Gerenciador de Tarefas

### **Problema: Navegador abre em branco / "Connection Refused"**
- Aguarde 10-30 segundos (servidor pode demorar)
- Verifique se InoLabel.exe está rodando
- Tente acessar: `http://127.0.0.1:8765`

### **Problema: "libGL não encontrado" (Linux)**
```bash
sudo apt-get install libgl1
```

### **Problema: "gcc não encontrado" (Linux)**
```bash
sudo apt-get install build-essential python3-dev cmake
```

### **Problema: Nenhuma imagem aparece**
- Confira se o caminho da pasta `dataset/` está **correto e absoluto**
- Confira se tem imagens de verdade lá dentro
- Reformate para um dos formatos aceitos

### **Problema: O build demora demais ou trava**
- PyTorch pode demorar 20+ minutos em conexões lentas
- Não feche o terminal (leia os logs em `dist/logs/`)
- Se travar por >1 hora, reinicie tudo

---

## 📚 Modos de Anotação

| Modo | Descrição | Melhor para |
|------|-----------|-----------|
| **Detecção** | Bounding boxes simples por frame | Objetos estáticos, imagens |
| **Rastreamento** | Mantém identidade entre frames (BYTETracker) | Vídeos com movimento |
| **OBB** | Caixas rotacionadas com ângulo | Objetos em diferentes orientações |
| **Classificação** | Organiza imagens em pastas por classe | Triagem de dados |

---

## ⌨️ Atalhos Principais

| Tecla | Ação |
|-------|------|
| `Espaço` | Próximo frame |
| `←` / `→` | Navegar entre frames |
| `Clique + arraste` | Desenhar bounding box |
| `Ctrl+Z` | Desfazer |
| `Delete` | Deletar caixa selecionada |
| `1-9` | Mudar classe ativa |
| `Scroll` | Zoom |
| `Esc` | Sair |

Veja todos os atalhos no menu da aplicação.

---

## 📦 Estrutura de Pastas

```
InoLabel/
├── README.md                          ← (você está aqui!)
├── instrucao.txt                      ← Guia detalhado em português
├── DESIGN.md                          ← Sistema de design
├── PRODUCT.md                         ← Definição do produto
├── requirements.txt                   ← Dependências Python
├── build.ps1                          ← Script de build (Windows)
├── build.sh                           ← Script de build (Linux)
├── main.py                            ← Ponto de entrada
│
├── app/                               ← Backend Python (FastAPI)
│   ├── api/                           ← API REST
│   ├── annotation/                    ← Lógica de anotação
│   ├── models.py                      ← Dataclasses
│   └── ...
│
├── frontend/                          ← Frontend React + Vite
│   ├── src/
│   ├── package.json
│   └── dist/                          ← Gerado após "npm run build"
│
├── APLICATIVO/ (Windows) ou dist/ (Linux)
│   └── InoLabel/
│       ├── InoLabel.exe (Windows)
│       ├── dataset/                   ← Suas imagens vão aqui
│       ├── outputs/                   ← Anotações salvas aqui
│       └── model.pt                   ← (opcional) seu modelo
```

---

## 📖 Documentação Adicional

- **[app/STRUCTURE.md](app/STRUCTURE.md)** — Arquitetura do código
- **[DESIGN.md](DESIGN.md)** — Sistema de design da UI
- **[PRODUCT.md](PRODUCT.md)** — Visão do produto
- **[instrucao.txt](instrucao.txt)** — Guia detalhado (em português)

---

## ❓ Perguntas Frequentes

**P: Preciso de GPU?**
A: Recomendado para detecção rápida, mas não é obrigatório. Roda em CPU.

**P: Meus dados são privados?**
A: 100%. Tudo roda localmente. Nada sai da sua máquina.

**P: Qual é o tamanho máximo de dataset?**
A: Depende da sua RAM. Testado com 10k+ imagens.

**P: Posso usar meu próprio modelo YOLO?**
A: Sim! Coloque `model.pt` na pasta de saída do executável.

**P: Como contribuir?**
A: Abra uma issue ou PR no GitHub!

---

## 🤝 Suporte

Encontrou algum problema?
- **Issues**: https://github.com/Inovisao/InoLabel/issues
- **Email**: magnumjabreuu@gmail.com

Descreva:
1. Sistema operacional (Windows/Linux)
2. A mensagem de erro **completa**
3. Em qual passo ocorreu

---

## 📜 Créditos

- **BYTETracker** — [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack)
- **YOLO** — [Ultralytics](https://github.com/ultralytics/ultralytics)
- **UI Components** — [Radix UI](https://www.radix-ui.com/)

---

**Feito com ❤️ pela Inovisão**

_A ferramenta que torna a anotação de datasets tão rápida quanto deveria ser._
