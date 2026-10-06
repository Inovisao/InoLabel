"""Erros de regra de negócio, independentes de HTTP.

Os serviços lançam estas exceções; `app.api.main` as converte em resposta HTTP com o
mesmo corpo que o FastAPI usa (`{"detail": ...}`).
"""

from __future__ import annotations


class DomainError(Exception):
    """Pedido recusado por uma regra do app. `status_code` é o equivalente HTTP."""

    status_code = 400

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class BadRequest(DomainError):
    """Pedido malformado ou fora do intervalo (400)."""

    status_code = 400


class NotFound(DomainError):
    """Recurso inexistente: sessão, anotação, arquivo (404)."""

    status_code = 404


class InvalidInput(DomainError):
    """Dados válidos no formato, mas recusados pela regra do modo/projeto (422)."""

    status_code = 422
