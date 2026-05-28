"""Endpoints de exportacao de dataset."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.session_manager import session_manager

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    output_dir: Optional[str] = None
    train_ratio: float = 0.7
    val_ratio: float = 0.2
    test_ratio: float = 0.1
    augmentation_factor: int = 0


@router.post("")
async def export_dataset(req: ExportRequest):
    """Inicia exportacao YOLO/COCO. Progresso e enviado via WebSocket."""
    tool = session_manager.tool
    if tool is None:
        raise HTTPException(400, "Nenhuma sessao ativa.")

    if not hasattr(tool, "export_yolo_dataset") and not hasattr(tool, "export"):
        raise HTTPException(400, "Modo atual nao suporta exportacao por este endpoint.")

    export_dir = Path(req.output_dir).expanduser() if req.output_dir else None

    try:
        if hasattr(tool, "export"):
            # ClassificationService
            if export_dir is None:
                raise HTTPException(400, "output_dir e obrigatorio para exportacao de classificacao.")
            result = tool.export(export_dir)
        else:
            # AnnotationTool / OBBAnnotationTool
            result = _run_annotation_export(tool, req, export_dir)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    session_manager.notify_frame_update()
    return {"status": "done", "result": str(result) if result else "ok"}


def _run_annotation_export(tool, req: ExportRequest, export_dir: Optional[Path]) -> str:
    """Executa a exportacao no tool de anotacao."""
    split = (req.train_ratio, req.val_ratio, req.test_ratio)
    total = sum(split)
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Soma dos splits deve ser 1.0, recebido {total:.2f}")

    if hasattr(tool, "export_yolo_dataset"):
        kwargs: dict = {}
        if export_dir:
            kwargs["output_dir"] = export_dir
        if req.augmentation_factor > 0:
            kwargs["augmentation_factor"] = req.augmentation_factor
        tool.export_yolo_dataset(**kwargs)
        return str(tool.yolo_dataset_dir)

    return "exported"
