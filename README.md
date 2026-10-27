# InoLabel

An image annotation tool developed by the **Computer Vision Laboratory — Inovisão**.
Supports five workflows: tracking, standard detection, oriented bounding boxes (OBB),
keypoints (pose), and image classification.

The app runs on your machine: a local server (FastAPI) serves the interface (React), which opens
in your browser at `http://127.0.0.1:8765`. No images leave your computer.

Organization, implementation, data preservation, documentation, and validation rules
are documented in [AGENTS.md](docs_to_ai/AGENTS.md) and apply to contributions.

---

## Installation — Linux (Ubuntu/Debian)

### 1. System dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip \
    build-essential python3-dev cmake \
    zenity git
```

> `build-essential`, `python3-dev`, and `cmake` are required to compile `lap` and `cython-bbox`.
> `zenity` (GNOME) or `kdialog` (KDE) opens the system folder picker.

Building the interface also requires **Node.js 20 or newer** (22 is used in CI), available
from [nodejs.org](https://nodejs.org/) or through `nvm`.

### 2. Install Miniconda (recommended)

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Close and reopen the terminal after installation
```

### 3. Create the Python environment

```bash
conda create -n inolabel python=3.9 -y
conda activate inolabel
```

### 4. Install project dependencies

```bash
git clone <repository-url>
cd tracking-anotator
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
```

### 5. Run

```bash
python main.py
```

The browser opens automatically at `http://127.0.0.1:8765`.

If you see `Interface não compilada` (interface not built), run `npm ci` and
`npm run build` inside `frontend/`, using Node.js 20 or newer. Then return to the
project root and run `python main.py` again. Python dependencies do not include the web interface.

---

## Installation — Windows 11

### 1. Install Python 3.9

1. Visit [python.org/downloads](https://www.python.org/downloads/) and download Python **3.9.x** (64-bit).
2. In the installer, select **"Add Python to PATH"** before clicking Install.
3. After installation, open **Command Prompt** and verify:
   ```cmd
   python --version
   ```

### 2. Install Visual C++ Build Tools

Required to compile `lap` and `cython-bbox`.

1. Visit [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
2. Download and run the installer.
3. Select **"Desktop development with C++"** and click Install.
4. Wait for installation to finish (this may take a few minutes).

### 3. Install CMake

1. Visit [cmake.org/download](https://cmake.org/download/) and download the `.msi` installer.
2. During installation, select **"Add CMake to the system PATH"**.

### 4. Install Node.js

1. Visit [nodejs.org](https://nodejs.org/) and install **Node.js 20 or newer** (22 is used in CI).

### 5. Install Git (optional, for cloning the repository)

1. Visit [git-scm.com](https://git-scm.com/) and install with the default options.

### 6. Clone and install the project

Open **Command Prompt** or **PowerShell**:

```cmd
git clone <repository-url>
cd tracking-anotator
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

### 7. Run

```cmd
python main.py
```

The browser opens automatically at `http://127.0.0.1:8765`.

---

## Build an executable

| System | Command | Behavior |
|--------|---------|----------|
| Windows (PowerShell) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and `.\scripts\build.ps1` | Creates the `inolabel` conda environment if needed, installs dependencies, runs `npm install` + `npm run build`, and runs PyInstaller |
| Linux / Git Bash | `bash scripts/build.sh` | Runs PyInstaller; requires a prebuilt frontend (`npm run build` inside `frontend/`) |

Output:

```
APLICATIVO/InoLabel/InoLabel.exe           # build.ps1 (Windows)
dist/InoLabel-linux/InoLabel/InoLabel      # build.sh (Linux)
```

> The executable includes application code and the interface, but no models or data.
> **Expected size:** between 1.5 GB and 3 GB (Ultralytics/PyTorch are large).

---

## Usage

The interface currently uses Portuguese labels; the relevant labels are included below for navigation.

1. **Workspace** — on first launch, choose the folder where projects are stored (similar to an Obsidian vault).
   Recent workspaces appear on subsequent launches; **Projetos → Trocar workspace** switches folders.
2. **Mode** — choose one of the five modes below.
3. **Data** — choose the dataset folder (or an image) and enter a **project name**. The project becomes
   a subfolder of the workspace.
4. **Classes** — add classes. In keypoint mode, also define the points for each class.
5. **Annotate** — changes are saved after each operation. To resume later, use **Projetos → Continuar**.
6. **Export** — press `Ctrl+E` or use the export button in the top toolbar.

The **Projetos** (Projects) and **Histórico** (History) pages list workspace projects with annotated frame
counts; **Atalhos** (Shortcuts) lists all keyboard shortcuts.

---

## Annotation modes

| Mode | Description |
|------|-------------|
| **Tracking** | Boxes with an object ID (`track_id`) maintained across frames |
| **Standard detection** | Independent boxes per frame, without IDs |
| **Oriented detection (OBB)** | Rotated boxes exported in YOLO OBB format |
| **Keypoints** | Named points per class, placed in order; exports YOLO Pose and COCO Keypoints |
| **Classification** | Each image is copied into its class folder |

In all box modes: drag to draw, click a box to select it and edit its class in the sidebar,
press `V` to move, `Del` to delete, and `N` to mark a frame as **reviewed without objects**
(it is exported as a negative sample).

### Tracking

- Each new box receives the **next available ID**; the **ID das próximas caixas** panel lets you fix
  an ID to follow the same object across frames.
- Change the selected box's ID in the panel (**Novo ID** generates the next available ID).

### Oriented detection (OBB)

- Draw an axis-aligned box and rotate it using the **○ handle** above it (`Shift` snaps to 15°),
  `Q`/`E` (5°; 1° with `Shift`), or the **Ângulo** field in the panel.
- With `V`, drag the rotated box to move it. The box stays within the image: near an edge it is
  pushed inward, and rotations that do not fit are rejected.

### Keypoints (pose)

- In the wizard, each class declares point names **in order**, separated by commas (default:
  `top_left, top_right, bottom_right, bottom_left`). Starting is blocked until all classes have points.
- Click to place points in order; a prompt at the top shows the next point. Placing the last point
  saves the instance.
- The **bounding box** is calculated from the placed points. Visibility follows the COCO convention:
  `0` absent, `1` occluded (hollow circle), `2` visible (filled circle).
- When resuming a project, point definitions come from the project itself. Changing the number of
  points in a class that already has annotations is rejected.

| Key | Action (keypoint mode) |
|-----|------------------------|
| Click | Place the next point for the class (`B` tool) |
| `X` | Skip the point (mark it absent) |
| `C` | Toggle visible/occluded for the selected point or upcoming points |
| `F` | Finish the instance now (remaining points are absent) |
| `Backspace` | Undo the last point in the current instance |
| `Esc` | Cancel the current instance |
| `V` + drag | Move a point in a saved instance |

### Classification

- Click a class or type its **number** (its position in the list). With up to 9 classes, a single key
  classifies immediately; with more classes, type the number and press `Enter` (confirmation is automatic when unambiguous).
- `/` searches for a class by name, `Space` skips the frame, and `Ctrl+Z` undoes an action.
- Reclassification **moves** the image to the new class without duplicating it.

### Model pre-annotation

The proposed extension to trained-model and prompt-based labeling is documented in
[Autolabeling architecture](docs_to_ai/AUTOLABELING_ARCHITECTURE.md). It is a design
proposal; the current capabilities are described below.
The [implementation plan](docs_to_ai/AUTOLABELING_IMPLEMENTATION_PLAN.md) defines
delivery phases, editor integration, and acceptance criteria.

**Detection projects now support local YOLO autolabeling in the editor.** Open
**Autolabeling** in the top toolbar for the integrated panel, or in the sidebar for
configuration and run history. Switching between these two views keeps the session open.

1. Select a trusted YOLO detection `.pt` checkpoint and click **Inspecionar modelo**.
2. Map model classes explicitly to project classes; leave unwanted classes ignored.
3. Set the confidence threshold and choose the current image, selected image numbers
   (starting at 1), or the whole dataset. Test the current image before a larger run.
4. Generate suggestions. Pending boxes appear with dashed amber outlines and stay
   separate from accepted annotations and exports.
5. Review each suggestion, adjust its class or pixel coordinates if needed, and
   accept or reject it. Selected suggestions can be accepted together. Acceptance
   can be undone from the panel or with `Ctrl+Z`; an annotation edited afterward
   must be handled manually to protect the correction.

Jobs run in a bounded local queue. The panel shows progress, errors, cancellation,
and resume controls. Interrupted runs are detected after reopening the project;
resume skips successful images and retries failed ones. A changed checkpoint or
input image requires a new run. Closing the application cancels further work after
any current inference operation finishes.

Model configuration and run/proposal manifests are stored in
`<project>/.inolabel/autolabeling/`. Accepted annotations use existing project state
and label persistence. Repeated acceptance recovers previously committed proposals
instead of creating duplicates. No detections does not mark an image reviewed.

The wizard's optional checkpoint remains supported as an initial model path.
The legacy tracking API (`POST /api/inference/tracking`) remains available, including
preview-only video inference. The new proposal UI currently supports detection on
images; tracking proposals, foundation models, full segmentation, Ollama, and OpenAI
are not yet implemented. No new external inference provider is contacted.

---

## Main shortcuts

| Key | Action |
|-----|--------|
| `→` / `D` | Next frame |
| `←` / `A` | Previous frame |
| `B` | Box tool (or point tool in keypoint mode) |
| `V` | Selection / move tool |
| Click | Select a box to edit its class / ID |
| `Del` | Remove the selected annotation |
| `Esc` | Deselect the annotation |
| `N` | Mark the frame as reviewed without objects (negative sample) |
| `Q` / `E` | OBB: rotate the selected box |
| `Ctrl+Z` | Undo (returns to the action's frame if necessary) |
| `Ctrl+E` | Open export |
| `Ctrl+,` | Session settings |

The full list, grouped by mode, is on the app's **Atalhos** (Shortcuts) page.

---

## Dataset export

| Option | Description |
|--------|-------------|
| **Formats** | YOLO and/or COCO together. Special modes: YOLO OBB and YOLO Pose / COCO Keypoints |
| **COCO layout** | **Roboflow** style (default): `_annotations.coco.json` alongside images; alternatively, an `images/` folder |
| **Destination / Name** | Defaults to the project's `exports/` folder |
| **Train/val/test split** | Splits images into configurable proportions totaling 100% |
| **Data augmentation** | Select transformations and 1–5 copies per image. Applies only to YOLO **training** images; enabling augmentation enables splitting |
| **ZIP package** | Also generates `<name>.zip`. References are checked first (image ↔ label, COCO `file_name` ↔ image), and `data.yaml` excludes the absolute path for portability |

- Dataset subfolders are preserved; COCO category IDs start at `1`.
- Frames marked as **reviewed without objects** are exported as negative samples (images without annotations).
- In keypoint mode, mirroring does not swap point names (a "left" point moves to the right);
  mirroring is therefore excluded from default augmentation in this mode.

Export runs in the background with a progress bar.

**Destination protection:**

- Export only deletes and recreates empty folders or folders created by an export (marked with the hidden `.inolabel_export` file).
- If the chosen name already exists and is not an InoLabel export, output goes to `<name>_<date>` and the existing folder is left untouched.
- Invalid destinations include the project folder and its ancestors, the source dataset (inside, equal to, or above it), the home folder, the disk root, and names such as `.` and `..`.

To validate an exported dataset, use `utils/verificar_export.py` (see Utilities).

---

## Generated output

```
<workspace>/
├── .inolabel/workspace.json                 # workspace index (rebuilt if missing)
└── <project>/
    ├── .inolabel.json                       # manifest: mode, dataset, classes, points, current frame
    ├── saved_data_states/                   # project state (source of truth)
    │   ├── annotations.coco.json            # detection / tracking (with track_id)
    │   ├── annotations_obb.coco.json        # OBB mode
    │   ├── annotations_keypoints.coco.json  # keypoint mode
    │   └── *.coco.json.bak                  # previous state backup, created when opening a session
    ├── labels/                              # .txt mirror in the mode's YOLO format
    ├── classification_state.json            # classification mode (+ one folder per class)
    └── exports/                             # default export destination
```

COCO state follows the version 1.0.0 format (category IDs starting at 1, `bbox` in pixels,
`file_name` relative to the dataset) and serves as the input for training scripts.

---

## Utilities

### Validate an exported dataset

Validates a COCO or YOLO export (including YOLO Pose and COCO Keypoints): images versus annotations,
IDs, boxes outside image bounds, categories, and points. Output contains aggregate results only, without filenames.

```bash
python utils/verificar_export.py <export-folder>
```

### Convert COCO → YOLO

```bash
python utils/convert_coco_to_yolo_dataset.py <project>/saved_data_states/annotations.coco.json \
    --image-root <image-folder> \
    --output-root <project>/yolo_dataset \
    --train-ratio 0.8 --val-ratio 0.1 --test-ratio 0.1
```

### Merge YOLO splits into a single training split

```bash
python utils/merge_yolo_splits.py <project>/yolo_dataset \
    --output-root <project>/yolo_dataset_train_only
```

### Convert tracking annotations → detection

```bash
python utils/convert_coco_tracking_to_detection.py <project>/saved_data_states/annotations.coco.json
```

### Repair legacy COCO Keypoints

`utils/fix_keypoint_coco.py` repairs inconsistent COCO Keypoints files: fills in `categories[].keypoints`,
removes duplicate closing points, and recalculates `bbox`/`num_keypoints`. By **default**, four-point
instances are ordered **TL → TR → BR → BL**; use `--no-sort-corners` to preserve their original order.

```bash
python utils/fix_keypoint_coco.py <project>/saved_data_states/annotations_keypoints.coco.json
```

### Download Open Images candidates for review

Downloads selfies with accessories (a large face touching an instance of the selected class) into
`openimages_candidates/<class>/`, leaving the dataset untouched. Review candidates, delete unsuitable
images, and move approved ones into the dataset. Each folder's `candidates.csv` records the license
(CC BY 2.0: retain attribution), author, and original bounding boxes.

```bash
python utils/fetch_openimages.py --classes hat --limit 150
python utils/fetch_openimages.py --classes hat glasses --splits validation test train  # train: streams a 2.2 GB CSV
```

Open Images does not include a mask class.

> **LGPD:** this utility downloads photographs of real people's faces. The CC BY 2.0 license covers copyright, not personal data protection. Before use, record the purpose, legal basis, and retention period; keep `openimages_candidates/` out of Git (already covered by `.gitignore`) and delete rejected candidates. This utility is not included in the distributed executable.

### Augment an output dataset

```bash
python utils/augment_output_dataset.py --annotations <project>/saved_data_states/annotations.coco.json \
    --images-dir <image-folder> --rotate90
```

> `utils/annotation_tool_bytetracked.py` is the old, **obsolete** monolithic tool. It contains bugs already fixed in the app (such as box clipping) and must not be used for annotation.

---

## Privacy and security

- **Local execution:** the server listens only on `127.0.0.1`; images and annotations stay on your machine.
- **Logs without filenames:** terminal messages identify images by `image_id` or an anonymous reference (`<arquivo 3f2a91c0>`), never by filename — filenames in datasets of people may contain personal data. The interface still shows filenames to the user.
- **Data outside Git:** do not commit datasets, project folders, or exports; keep them outside the repository.
- **Model weights:** `.pt` files use pickle and execute code when loaded. Only open weights from trusted sources.
- **Unreadable state:** if `annotations*.coco.json` cannot be read, the session does not open and the file is left unchanged. Restore the adjacent `.bak` file (generated when opening each session) or repair the JSON.

---

## Configuration

The web app no longer uses the Tkinter app parameters in `app/config.py`. Paths can be overridden
with environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `INOLABEL_LOCAL_DIR` | `.local/` next to the app | Recent workspaces and keyboard shortcuts |
| `INOLABEL_OUTPUT_BASE` | `outputs/` next to the app | Output folder when none is specified |
| `INOLABEL_ASSETS_DIR` | `assets/` | Static assets |
| `INOLABEL_ENV=development` | — | `python main.py` with server auto-reload |

---

## Development

Code is organized by feature:

```
app/api/<feature>/            router.py (HTTP) → service.py (use cases) + schemas.py and domain modules
                              annotations, classification, session, frames, export, inference,
                              workspace, projects, classes, modes, keybinds, browse
app/api/common/               shared schemas and business rule errors (DomainError)
app/api/state.py              session state in memory
app/core/project_state/       project state in annotations.coco.json
app/annotation/               YOLO/COCO exporters, splitting, and augmentation
frontend/src/features/        annotate, export, wizard, projects, workspace, help
frontend/src/shared/          API client, types, sessions, layout, and UI components
```

Run with auto-reload (backend and frontend, in separate terminals):

```bash
INOLABEL_ENV=development python main.py      # API at 127.0.0.1:8765
cd frontend && npm run dev                   # interface at localhost:5173 (proxies /api to port 8765)
```

Tests and checks:

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
cd frontend && npx tsc --noEmit && npm run build
```

CI (`.github/workflows/ci.yml`) runs Python tests and frontend type checks, unit tests, and builds
on pushes and pull requests to `main` and `master`.

---

## Troubleshooting

The Autolabeling panel includes runtime diagnostics for the Python interpreter
serving the API. If it reports missing Ultralytics/PyTorch packages, installing
packages in a different terminal environment will not repair the running server.
Stop the server, activate the prepared Python 3.9 environment, and restart it.
The requirements pins are validated on Python 3.9; do not try to repair a Python
3.14 environment by installing incompatible pinned wheels.

For an existing incompatible environment, keep it intact and create a separate one:

```bash
conda create -n inolabel-runtime python=3.9 pip -y
conda activate inolabel-runtime
python -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install cython numpy==2.0.2
python -m pip install --no-build-isolation cython-bbox==0.1.5
python -m pip install -r requirements.txt
python main.py
```

This example installs the CPU runtime. GPU installations need the corresponding
PyTorch variant described in `requirements.txt`.

| Problem | Solution |
|---------|----------|
| Blank page or "Not Found" on startup | The frontend has not been built: run `npm install && npm run build` inside `frontend/` |
| Folder picker does not open on Linux | Install `zenity` (GNOME) or `kdialog` (KDE) |
| Port 8765 is in use | Close the other InoLabel instance (or the process using the port) |
| `lap`/`cython_bbox` fails on Linux | Install `build-essential python3-dev cmake` and try again |
| `lap`/`cython_bbox` fails on Windows | Install Visual C++ Build Tools and CMake as described above |
| Session does not open because of an `annotations.coco.json` error | Unreadable state: restore the adjacent `.bak` file |

---

## Credits

- BYTETracker from [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack)
- Detection and OBB via [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
