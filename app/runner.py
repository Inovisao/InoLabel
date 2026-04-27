import sys

from app.annotation_tool import AnnotationTool
from app.startup_dialog import ask_startup_config


def main() -> int:
    session_config = ask_startup_config()

    tool = None
    try:
        tool = AnnotationTool(session_config=session_config)
        tool.run()
        return 0
    except KeyboardInterrupt:
        if tool is not None:
            tool.finish_processing("Processo interrompido.")
        return 1
    except Exception as exc:  # pylint: disable=broad-except
        if tool is not None:
            tool.finish_processing(f"Erro: {exc}")
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
