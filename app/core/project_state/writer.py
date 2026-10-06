"""Grava o ``annotations.coco.json`` do projeto em segundo plano.

O payload é montado na hora da alteração (snapshot consistente com a memória); só
a serialização e o disco vão para a thread de fundo, porque crescem com o projeto
e travariam a interface a cada caixa desenhada. Gravações pendentes para o mesmo
arquivo colapsam na mais recente, a escrita é atômica (``.tmp`` + ``replace``) e
um snapshot antigo nunca sobrescreve um mais novo.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple

log = logging.getLogger(__name__)


def write_json_atomic(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


class CocoStateWriter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._changed = threading.Condition(self._lock)
        self._pending: Dict[Path, Tuple[int, dict]] = {}
        self._written: Dict[Path, int] = {}
        self._writing = 0
        self._seq = 0
        self._thread: Optional[threading.Thread] = None
        self.last_error: Optional[str] = None

    def submit(self, path: Path, payload: dict) -> None:
        with self._changed:
            self._seq += 1
            self._pending[Path(path)] = (self._seq, payload)
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="coco-state-writer", daemon=True)
                self._thread.start()
            self._changed.notify_all()

    def flush(self, timeout: Optional[float] = 30.0) -> bool:
        """Espera as gravações pendentes terminarem. False se estourar o tempo."""
        with self._changed:
            return self._changed.wait_for(lambda: not self._pending and not self._writing, timeout=timeout)

    def _run(self) -> None:
        while True:
            with self._changed:
                if not self._pending:
                    self._changed.wait(timeout=5.0)
                    if not self._pending:
                        self._thread = None
                        return
                path, (seq, payload) = self._pending.popitem()
                if seq <= self._written.get(path, 0):
                    self._changed.notify_all()
                    continue
                self._writing += 1
            try:
                write_json_atomic(path, payload)
                with self._changed:
                    self._written[path] = max(seq, self._written.get(path, 0))
                    self.last_error = None
            except Exception as exc:  # pylint: disable=broad-except
                log.exception("falha ao gravar o estado do projeto")
                with self._changed:
                    self.last_error = f"{type(exc).__name__}: {exc}"
            finally:
                with self._changed:
                    self._writing -= 1
                    self._changed.notify_all()
