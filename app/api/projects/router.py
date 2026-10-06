"""Rotas HTTP de validação de caminhos e listagem de projetos (sob /api/session)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.projects import listing, paths
from app.api.projects.schemas import OutputsRequest, PathValidationRequest

router = APIRouter(prefix="/api/session", tags=["validation"])


def _invalid(exc: paths.InvalidPath) -> JSONResponse:
    return JSONResponse(status_code=422, content={"valid": False, "error": exc.detail})


@router.post("/validate-path")
def validate_path(body: PathValidationRequest):
    try:
        return paths.validate_path(body.path)
    except paths.InvalidPath as exc:
        return _invalid(exc)


@router.post("/validate-model")
def validate_model(body: PathValidationRequest):
    try:
        return paths.validate_model(body.path)
    except paths.InvalidPath as exc:
        return _invalid(exc)


@router.get("/outputs")
def list_outputs(output_path: str):
    return listing.list_outputs(output_path)


@router.post("/outputs")
def list_outputs_from_body(body: OutputsRequest):
    return listing.list_outputs(body.output_path)


@router.get("/projects")
def list_projects(path: str = "") -> list:
    return listing.list_projects(path)
