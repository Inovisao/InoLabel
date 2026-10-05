"""Marca do Laboratorio Inovisao — logo recortado e cacheado para uso em tamanho pequeno.

O PNG original tem 1920x1080 com muita borda transparente; sem recortar pela caixa
do canal alfa o desenho fica minusculo quando reduzido para a altura da topbar.
"""

from __future__ import annotations

import tkinter as tk
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.ui.theme.tokens import COLORS, FONTS, SIZES, SPACING


def _logo_path() -> Path:
    from app.config import LOGO_PATH  # pylint: disable=import-outside-toplevel
    return LOGO_PATH


@lru_cache(maxsize=8)
def load_brand_image(height: int, path: Optional[str] = None):
    """Logo recortado e redimensionado para `height` px (PIL RGBA), ou None se indisponivel.

    Cacheia a imagem PIL — PhotoImage fica por conta de quem exibe, pois e presa ao
    interpretador Tk que a criou.
    """
    try:
        from PIL import Image  # pylint: disable=import-outside-toplevel

        source = Path(path) if path is not None else _logo_path()
        if not source.exists() or height <= 0:
            return None
        img = Image.open(source).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if bbox is None:
            return None
        img = img.crop(bbox)
        width = max(1, round(img.width * height / img.height))
        return img.resize((width, height), Image.LANCZOS)
    except Exception:  # pylint: disable=broad-except
        return None


def make_brand_mark(parent: tk.Widget, *, height: Optional[int] = None, bg: Optional[str] = None) -> tk.Frame:
    """Logo + "InoLabel". Sem o arquivo do logo, mostra so o nome."""
    from PIL import ImageTk  # pylint: disable=import-outside-toplevel

    bg = bg or COLORS["panel"]
    height = height or SIZES["brand_h"]
    frame = tk.Frame(parent, bg=bg)

    image = load_brand_image(height)
    if image is not None:
        photo = ImageTk.PhotoImage(image, master=parent)
        logo = tk.Label(frame, image=photo, bg=bg, bd=0)
        logo.image = photo  # mantem referencia viva
        logo.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
        frame.logo_label = logo

    tk.Label(frame, text="InoLabel", font=FONTS["brand"], bg=bg, fg=COLORS["text"]).pack(side=tk.LEFT)
    return frame


def set_window_icon(window: tk.Misc, size: int = 64) -> bool:
    """Usa o logo, centralizado num quadrado, como icone da janela."""
    try:
        from PIL import Image, ImageTk  # pylint: disable=import-outside-toplevel

        image = load_brand_image(size)
        if image is None:
            return False
        image = image.copy()
        image.thumbnail((size, size), Image.LANCZOS)
        square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        square.paste(image, ((size - image.width) // 2, (size - image.height) // 2), image)
        photo = ImageTk.PhotoImage(square, master=window)
        window.iconphoto(True, photo)
        window._brand_icon = photo  # mantem referencia viva
        return True
    except Exception:  # pylint: disable=broad-except
        return False
