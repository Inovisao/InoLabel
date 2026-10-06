"""Salvamento automático a cada mudança de anotação."""

from __future__ import annotations

import logging

import cv2

from app.api import state as _state
from app.api.annotations.labels import write_label_file
from app.api.annotations.project_state import save_project_state

log = logging.getLogger(__name__)


def autosave(image_id: int) -> None:
    """Grava o frame depois de uma mudança: .txt espelho e annotations.coco.json.

    Falhas vão para o log e nunca viram erro HTTP — a anotação já está na memória.
    """
    try:
        session = _state.active_session()
        if session is None:
            return
        if not _state.frame_paths or image_id >= len(_state.frame_paths):
            return
        dims = _state.frame_dims.get(image_id)
        if dims is None:
            # Frame not yet loaded through the UI — read dims from disk so we never
            # silently discard annotations added before the frame is displayed.
            img_path = _state.frame_paths[image_id]
            img = cv2.imread(str(img_path))
            if img is None:
                log.warning("autosave: cannot read image %s for frame %d — skipped", img_path.name, image_id)
                return
            h, w = img.shape[:2]
            dims = (w, h)
            _state.frame_dims[image_id] = dims

        img_w, img_h = dims
        if img_w == 0 or img_h == 0:
            return

        write_label_file(session, image_id, img_w, img_h)
        save_project_state()
    except Exception:
        log.exception("autosave failed for frame %d", image_id)
