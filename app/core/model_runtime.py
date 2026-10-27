"""Read-only diagnostics for the interpreter that actually serves inference."""

import sys
from importlib.metadata import PackageNotFoundError, version

MODEL_PACKAGES = ('ultralytics', 'torch', 'torchvision', 'numpy', 'opencv-python', 'Pillow')


def runtime_info() -> dict:
    packages = {}
    for name in MODEL_PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        'python_version': sys.version.split()[0],
        'executable': sys.executable,
        'project_python': '3.9',
        'packages': packages,
        'missing': [name for name, installed in packages.items() if installed is None],
    }


class ModelRuntimeError(RuntimeError):
    """The selected Python environment cannot import the model runtime."""


def import_error_message(error: ImportError) -> str:
    info = runtime_info()
    missing = ', '.join(info['missing'])
    detail = f" Dependências ausentes: {missing}." if missing else ''
    return (
        f"Não foi possível importar o runtime YOLO no Python {info['python_version']}."
        f"{detail} Interpretador: {info['executable']}. "
        "Use o ambiente Python 3.9 do projeto e instale as dependências com "
        "python -m pip install -r requirements.txt. Reinicie o aplicativo nesse ambiente. "
        f"Erro original: {error}"
    )
