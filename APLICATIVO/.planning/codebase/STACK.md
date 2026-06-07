---
last_mapped_commit: af6f39f6d52b32e68a7d38ed4a1b747fd1283f01
---

# Technology Stack

**Analysis Date:** 2026-06-02

## Languages

**Primary:**
- Python 3.9 - Main annotation application, FastAPI backend, image processing, model inference, export tooling, and tests in `main.py`, `api_server.py`, `app/`, `tracker/`, `utils/`, and `tests/`. Python 3.9 is specified by `README.md`, `build.sh`, and `.github/workflows/ci.yml`.
- TypeScript ES2022 - React frontend in `frontend/src/` with compiler settings in `frontend/tsconfig.json`.

**Secondary:**
- Rust 1.77.2 - Tauri desktop shell and sidecar launcher in `frontend/src-tauri/`, with `rust-version = "1.77.2"` in `frontend/src-tauri/Cargo.toml`.
- JavaScript - Demo accessibility test harness in `.impeccable/demo/` and package scripts in `.impeccable/demo/package.json`.
- Bash - Cross-platform PyInstaller packaging automation in `build.sh`.

## Runtime

**Environment:**
- Python 3.9 runtime for the classic Tkinter desktop app (`main.py`) and FastAPI sidecar server (`api_server.py`).
- Node.js 18 in CI for demo browser tests via `.github/workflows/ci.yml`; frontend development uses npm scripts from `frontend/package.json`.
- Rust/Tauri 2 runtime for the desktop shell in `frontend/src-tauri/src/lib.rs`.

**Package Manager:**
- pip with `requirements.txt`; Python dependencies are unpinned and no Python lockfile is detected.
- npm with `frontend/package-lock.json` for the React/Tauri frontend.
- npm with `.impeccable/demo/package-lock.json` for demo accessibility tests.
- Cargo for `frontend/src-tauri/Cargo.toml`; no `frontend/src-tauri/Cargo.lock` is detected.
- Lockfile: `frontend/package-lock.json` present, `.impeccable/demo/package-lock.json` present, Python lockfile missing, Rust lockfile missing.

## Frameworks

**Core:**
- Tkinter - Primary desktop UI used by `app/runner.py`, `app/ui/startup/wizard.py`, and the annotation tool modules under `app/annotation/`, `app/annotation_obb/`, and `app/classification/`.
- FastAPI - Local HTTP backend in `app/api/main.py` with routers in `app/api/routes/`.
- Uvicorn - Local ASGI server launched by `api_server.py` on `127.0.0.1:8765`.
- React 19.2.7 - Frontend UI in `frontend/src/`, declared in `frontend/package.json` and locked in `frontend/package-lock.json`.
- Vite 6.4.3 - Frontend dev/build tool configured in `frontend/vite.config.ts`.
- Tauri 2 - Desktop shell configured in `frontend/src-tauri/tauri.conf.json` and implemented in `frontend/src-tauri/src/lib.rs`.

**Testing:**
- pytest - CI invokes `python -m pytest -q` in `.github/workflows/ci.yml`; tests are Python `unittest`-style files under `tests/`.
- Playwright 1.37.0 - Demo accessibility tests in `.impeccable/demo/package.json` and `.impeccable/demo/tests/accessibility.test.js`.

**Build/Dev:**
- TypeScript 5.9.3 - Frontend type checking via `npm run build` in `frontend/package.json`.
- Tailwind CSS 4.3.0 and `@tailwindcss/vite` - CSS pipeline configured by `frontend/vite.config.ts` and `frontend/src/styles.css`.
- `@vitejs/plugin-react` 4.7.0 - React integration in `frontend/vite.config.ts`.
- PyInstaller >=5.0 - Native Python app packaging in `build.sh` and `README.md`.
- Tauri CLI 2.11.2 - Desktop packaging command exposed by `frontend/package.json`.

## Key Dependencies

**Critical:**
- `ultralytics` - YOLO model loading and inference in `app/annotation/state/core_init.py`, `app/ui/startup/wizard.py`, and detection helpers under `app/annotation/detection/` and `app/annotation_obb/detection/`.
- `opencv-python` / `cv2` - Frame loading, encoding, video capture, image writing, NMS, ROI operations, and augmentation in `app/api/routes/frames.py`, `app/annotation/`, `app/annotation_obb/`, and `app/annotation/infrastructure/export/yolo_exporter.py`.
- `Pillow` - Tkinter image display and logo handling in `app/ui/startup/wizard.py`, `app/ui/startup/splash.py`, and `app/classification/tools/navigation.py`.
- `numpy`, `scipy`, `lap`, and `cython-bbox` - Geometry, tracking, matching, and BYTETracker support in `tracker/` and `app/tracking/`.
- `fastapi`, `uvicorn[standard]`, and `python-multipart` - Backend API stack in `app/api/main.py` and `api_server.py`.

**Infrastructure:**
- `zustand` 5.0.14 - Frontend state stores in `frontend/src/stores/session.ts` and `frontend/src/stores/annotation.ts`.
- `konva` 9.3.22 and `react-konva` 19.2.4 - Canvas annotation surface in `frontend/src/components/canvas/AnnotationCanvas.tsx`.
- `framer-motion` 12.40.0 - Wizard transitions in `frontend/src/components/wizard/Wizard.tsx`.
- `lucide-react` 0.475.0 - Frontend icons in `frontend/src/components/wizard/StepConfig.tsx`.
- Radix UI packages - Dialog, dropdown, select, slider, switch, and tooltip primitives declared in `frontend/package.json`.
- `@tauri-apps/plugin-shell` 2 - Starts the Python sidecar in `frontend/src-tauri/src/lib.rs`.

## Configuration

**Environment:**
- Python runtime configuration uses constants in `app/config.py` for paths, supported extensions, model path, output state directory, confidence threshold, ROI defaults, and UI sizing.
- Frontend environment prefix is restricted to `VITE_` and `TAURI_ENV_*` in `frontend/vite.config.ts`.
- `TAURI_ENV_DEBUG` controls Vite minification and sourcemaps in `frontend/vite.config.ts`.
- No `.env` files are present in the repository root. Do not add required secrets unless the integration docs are updated.

**Build:**
- Python dependencies: `requirements.txt`.
- Python executable build: `build.sh`, with additional PyInstaller guidance in `README.md`.
- Frontend package config: `frontend/package.json`.
- Frontend compiler config: `frontend/tsconfig.json`.
- Frontend dev/build config: `frontend/vite.config.ts`.
- Tauri package config: `frontend/src-tauri/Cargo.toml` and `frontend/src-tauri/tauri.conf.json`.
- CI config: `.github/workflows/ci.yml`.

## Platform Requirements

**Development:**
- Python 3.9 with Tkinter; Linux requires `python3-tk` per `README.md`.
- Native build tools, Python headers, and CMake are required for `lap` and `cython-bbox`, documented in `README.md` and installed by `build.sh`.
- Node.js 18 is the CI baseline in `.github/workflows/ci.yml`; npm is required for `frontend/package.json`.
- Rust 1.77.2 is required for Tauri, specified in `frontend/src-tauri/Cargo.toml`.
- Local model weights and datasets live outside version control: `model.pt`, `dataset/`, `outputs/`, `data/`, `models/`, and `videos/` are ignored by `.gitignore`.

**Production:**
- Python desktop distribution is a PyInstaller onedir bundle generated by `build.sh`; `README.md` documents `dist/InoLabel-linux/InoLabel/InoLabel` and `dist/InoLabel-windows/InoLabel/InoLabel.exe`.
- Tauri desktop distribution bundles the Vite output from `frontend/dist` and expects an `api_server` sidecar declared in `frontend/src-tauri/src/lib.rs` and enabled in `frontend/src-tauri/tauri.conf.json`.
- The YOLO model file and dataset are intentionally external to the executable and must sit next to the packaged executable as described in `README.md`.

---

*Stack analysis: 2026-06-02*
