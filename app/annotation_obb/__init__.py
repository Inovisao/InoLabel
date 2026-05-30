"""Oriented bounding box (OBB) annotation mode."""

__all__ = ["OBBAnnotationTool"]


def __getattr__(name):
    if name == "OBBAnnotationTool":
        from app.annotation_obb.tool import OBBAnnotationTool

        return OBBAnnotationTool
    raise AttributeError(name)
