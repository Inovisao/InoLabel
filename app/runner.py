import sys

from app.annotation_tool import AnnotationTool


def main() -> int:
    tool = None
    try:
        tool = AnnotationTool()
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
