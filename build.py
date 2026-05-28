"""
Script de build do InoLabel.

Uso:
    python build.py             # build completo (frontend + PyInstaller)
    python build.py --frontend  # apenas npm run build
    python build.py --pyinst    # apenas PyInstaller (reutiliza frontend/dist existente)
    python build.py --dev       # inicia o servidor em modo dev (sem pywebview)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
DIST = ROOT / "frontend" / "dist"


def run(cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"\n[build] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if result.returncode != 0:
        print(f"[ERRO] Falha ({result.returncode}): {' '.join(cmd)}", file=sys.stderr)
        sys.exit(result.returncode)


def build_frontend() -> None:
    print("\n=== Frontend (npm run build) ===")
    if not (FRONTEND / "node_modules").exists():
        run(["npm", "install"], cwd=FRONTEND)
    run(["npm", "run", "build"], cwd=FRONTEND)
    print(f"[OK] Frontend gerado em {DIST}")


def build_pyinstaller() -> None:
    print("\n=== PyInstaller ===")
    if not DIST.exists():
        print("[ERRO] frontend/dist nao encontrado. Execute primeiro: python build.py --frontend")
        sys.exit(1)
    run([sys.executable, "-m", "PyInstaller", "InoLabel.spec", "--noconfirm"])
    exe = ROOT / "dist" / "InoLabel" / "InoLabel.exe"
    if exe.exists():
        print(f"\n[OK] Executavel gerado em:\n  {exe}")
    else:
        print(f"\n[OK] Build concluido. Saida em: {ROOT / 'dist' / 'InoLabel'}")


def start_dev() -> None:
    """Inicia o servidor FastAPI em modo dev (sem pywebview, com hot-reload na porta 7432)."""
    print("\n=== Modo dev ===")
    print(f"  API:      http://127.0.0.1:7432/api/health")
    print(f"  Docs:     http://127.0.0.1:7432/docs")
    print(f"  Frontend: http://localhost:5173  (npm run dev em outro terminal)")
    run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", "7432",
        "--reload",
        "--reload-dir", "backend",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="InoLabel build script")
    parser.add_argument("--frontend", action="store_true", help="Apenas build do frontend")
    parser.add_argument("--pyinst", action="store_true", help="Apenas PyInstaller")
    parser.add_argument("--dev", action="store_true", help="Inicia servidor de desenvolvimento")
    args = parser.parse_args()

    if args.dev:
        start_dev()
    elif args.frontend:
        build_frontend()
    elif args.pyinst:
        build_pyinstaller()
    else:
        build_frontend()
        build_pyinstaller()


if __name__ == "__main__":
    main()
