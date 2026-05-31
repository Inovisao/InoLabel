"""Splash screen shown while heavy dependencies load in background."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path

from app.ui.theme.tokens import COLORS

_WIDTH  = 480
_HEIGHT = 280


def _center_geometry(root: tk.Tk) -> None:
    root.update_idletasks()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - _WIDTH) // 2
    y = (sh - _HEIGHT) // 2
    root.geometry(f"{_WIDTH}x{_HEIGHT}+{x}+{y}")


def _load_logo(canvas: tk.Canvas, logo_path: Path) -> int:
    """Render logo blended onto the splash background; return bottom-y (or 0 on failure)."""
    from PIL import Image, ImageTk  # pylint: disable=import-outside-toplevel
    try:
        img = Image.open(logo_path).convert("RGBA")
    except Exception:
        try:
            from app.config import BASE_DIR
            alt_logo = BASE_DIR / "assets" / "inovisao.png"
            img = Image.open(alt_logo).convert("RGBA")
        except Exception:
            print(f"[WARN] Logo não encontrada em {logo_path} nem em {alt_logo if 'alt_logo' in locals() else 'N/A'}")
            return 0
    img.thumbnail((200, 90), Image.LANCZOS)
    # Blend transparent pixels onto the white panel background
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    photo = ImageTk.PhotoImage(bg.convert("RGB"))
    canvas._logo_photo = photo
    item = canvas.create_image(_WIDTH // 2, 56, image=photo, anchor=tk.CENTER)
    return canvas.bbox(item)[3] + 8


def show_splash() -> None:
    """Show splash window, load heavy deps in background, then close."""

    from app.config import LOGO_PATH  # pylint: disable=import-outside-toplevel

    root = tk.Tk()
    root.overrideredirect(True)
    root.configure(bg=COLORS["panel"])
    _center_geometry(root)

    canvas = tk.Canvas(root, width=_WIDTH, height=_HEIGHT, bg=COLORS["panel"],
                       highlightthickness=0, bd=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    logo_bottom = _load_logo(canvas, LOGO_PATH) if LOGO_PATH.exists() else 0

    if logo_bottom == 0:
        # text-only fallback: eye outline
        cx = _WIDTH // 2
        canvas.create_oval(cx - 22, 30, cx + 22, 74, outline=COLORS["accent"], width=2)
        canvas.create_oval(cx - 8, 44, cx + 8, 60, fill=COLORS["accent"], outline="")
        logo_bottom = 82

    # divider line below logo
    canvas.create_line(
        _WIDTH // 4, logo_bottom + 6,
        _WIDTH * 3 // 4, logo_bottom + 6,
        fill=COLORS["accent"], width=2,
    )

    title_y = logo_bottom + 30
    canvas.create_text(_WIDTH // 2, title_y, text="InoLabel",
                       fill=COLORS["primary"], font=("Helvetica", 26, "bold"), anchor=tk.CENTER)

    sub_y = title_y + 32
    canvas.create_text(_WIDTH // 2, sub_y, text="Laboratório de Visão Computacional",
                       fill=COLORS["muted"], font=("Helvetica", 11), anchor=tk.CENTER)

    dot_y = _HEIGHT - 28
    dot_item = canvas.create_text(_WIDTH // 2, dot_y, text="Carregando.",
                                  fill=COLORS["muted"], font=("Helvetica", 11), anchor=tk.CENTER)

    # bottom bar in brand blue with thin orange accent
    canvas.create_rectangle(0, _HEIGHT - 10, _WIDTH, _HEIGHT, fill=COLORS["primary"], outline="")
    canvas.create_line(0, _HEIGHT - 10, _WIDTH, _HEIGHT - 10, fill=COLORS["accent"], width=2)

    _dots = ["Carregando.", "Carregando..", "Carregando..."]
    _step = [0]

    ready = threading.Event()

    def _animate():
        if ready.is_set():
            root.destroy()
            return
        _step[0] = (_step[0] + 1) % len(_dots)
        canvas.itemconfig(dot_item, text=_dots[_step[0]])
        root.after(400, _animate)

    def _heavy_load():
        try:
            import app.ui.startup.wizard  # noqa: F401  triggers ultralytics import
            import app.annotation_tool     # noqa: F401
        except Exception:  # pylint: disable=broad-except
            pass
        ready.set()

    threading.Thread(target=_heavy_load, daemon=True).start()
    root.after(400, _animate)
    root.mainloop()
