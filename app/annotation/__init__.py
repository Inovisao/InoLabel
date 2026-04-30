__all__ = ["AnnotationTool"]


def __getattr__(name):
    if name == "AnnotationTool":
        from app.annotation.tool import AnnotationTool

        return AnnotationTool
    raise AttributeError(name)
