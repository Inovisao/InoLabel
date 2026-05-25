"""Welcome/intro screen shown after loading, before the wizard."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

_BG     = "#0A1628"
_BLUE   = "#1560BD"
_ORANGE = "#F07820"
_WHITE  = "#FFFFFF"
_MUTED  = "#7A93B0"
_BORDER = "#1E3A5C"

# Base dimensions at 1080p/96dpi — scaled up at runtime
_BASE_W, _BASE_H = 860, 540


class _RoundedButton(tk.Canvas):
    """Canvas button with rounded corners and hover animation.

    Must be parented to the Toplevel (not to another Canvas), then embedded
    in a Canvas via create_window() — this avoids Tcl path issues.
    """

    def __init__(self, parent, text: str, command=None, *,
                 radius: int = 10,
                 bg: str = _BLUE, hover_bg: str = _ORANGE,
                 fg: str = _WHITE,
                 font=("Helvetica", 13, "bold"),
                 padx: int = 48, pady: int = 14):
        f  = tkfont.Font(family=font[0], size=font[1],
                         weight=font[2] if len(font) > 2 else "normal")
        tw = f.measure(text)
        th = f.metrics("linespace")
        w  = tw + padx * 2
        h  = th + pady * 2

        super().__init__(
            parent,
            width=w, height=h,
            bg=_BG, highlightthickness=0, bd=0,
            cursor="hand2",
        )
        self._btn_bg   = bg
        self._hover_bg = hover_bg
        self._btn_fg   = fg
        self._radius   = radius
        self._command  = command
        self._font     = font
        self._text     = text
        self._btn_w    = w   # NOT self._w — that's Tkinter's internal Tcl path
        self._btn_h    = h

        self._render(bg)

        self.bind("<Enter>",    lambda _e: self._render(self._hover_bg))
        self.bind("<Leave>",    lambda _e: self._render(self._btn_bg))
        self.bind("<Button-1>", self._on_click)

    def _render(self, fill: str):
        self.delete("all")
        r = self._radius
        w, h = self._btn_w, self._btn_h
        self.create_polygon(
            r,     0,     w - r, 0,
            w,     r,     w,     h - r,
            w - r, h,     r,     h,
            0,     h - r, 0,     r,
            fill=fill, outline=fill, smooth=True,
        )
        self.create_text(
            w // 2, h // 2,  # pylint: disable=invalid-name
            text=self._text,
            fill=self._btn_fg,
            font=self._font,
            anchor=tk.CENTER,
        )

    def _on_click(self, _event=None):
        if self._command:
            self._command()


class IntroScreen:
    def __init__(self):
        self._started = False
        self.root = tk.Tk()
        self.root.title("InoLabel")
        self.root.configure(bg=_BG)

        from app.ui.layout.responsive_window import apply_responsive_geometry  # pylint: disable=import-outside-toplevel
        from app.ui.layout.scale import compute_ui_scale, get_screen_dpi       # pylint: disable=import-outside-toplevel

        metrics = apply_responsive_geometry(self.root, width_ratio=0.92, height_ratio=0.88)
        self._W = metrics.window_width
        self._H = metrics.window_height
        self._scale = max(1.0, compute_ui_scale(metrics.height, get_screen_dpi(self.root)))

        self._build()
        self.root.bind("<Return>", lambda _e: self._start())
        self.root.bind("<space>",  lambda _e: self._start())
        self.root.bind("<Escape>", lambda _e: self._close())

    # ── build ─────────────────────────────────────────────────────

    def _build(self):
        W, H = self._W, self._H
        cv = tk.Canvas(self.root, width=W, height=H, bg=_BG,
                       highlightthickness=0, bd=0,
                       scrollregion=(0, 0, W, H))
        cv.pack(fill=tk.BOTH, expand=True)

        self._draw_background(cv)
        logo_bottom = self._draw_logo(cv)
        self._draw_text(cv, logo_bottom)
        self._draw_button(cv)
        self._draw_footer(cv)

    def _s(self, value: int) -> int:
        """Scale a pixel value by the effective display scale."""
        return max(1, int(round(value * self._scale)))

    def _f(self, family: str, size: int, *style: str) -> tuple:
        """Return a scaled font tuple."""
        return (family, self._s(size)) + style

    def _draw_background(self, cv: tk.Canvas):
        W, H = self._W, self._H
        # Blue glow — top right
        cv.create_oval(W - self._s(260), -self._s(140),
                       W + self._s(80),   self._s(180), fill="#0E2B56", outline="")
        cv.create_arc(W - self._s(200), -self._s(80),
                      W + self._s(40),    self._s(160),
                      start=170, extent=130, outline=_BLUE, width=1, style=tk.ARC)

        # Orange glow — bottom left
        cv.create_oval(-self._s(120), H - self._s(180),
                        self._s(120), H + self._s(60), fill="#2A1200", outline="")
        cv.create_arc(-self._s(80), H - self._s(140),
                       self._s(80), H + self._s(20),
                      start=350, extent=140, outline=_ORANGE, width=1, style=tk.ARC)

        # Horizontal rule
        pad = self._s(60)
        cv.create_line(pad, H // 2 + self._s(20),
                       W - pad, H // 2 + self._s(20), fill=_BORDER, width=1)

        # Accent dots — scaled positions
        dots = [
            (self._s(40),  self._s(80),  _BLUE),
            (W - self._s(40), self._s(100), _ORANGE),
            (self._s(60),  H - self._s(70), _BLUE),
            (W - self._s(40), H - self._s(120), _ORANGE),
        ]
        r = self._s(3)
        for x, y, color in dots:
            cv.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")

    def _draw_logo(self, cv: tk.Canvas) -> int:
        """Render logo; return bottom-y for layout below it."""
        from app.config import LOGO_PATH  # pylint: disable=import-outside-toplevel

        cy = self._s(138)
        if not LOGO_PATH.exists():
            return cy

        try:
            from PIL import Image, ImageTk  # pylint: disable=import-outside-toplevel

            img = Image.open(LOGO_PATH).convert("RGBA")
            img.thumbnail((self._s(300), self._s(128)), Image.LANCZOS)

            # Blend transparent pixels against the dark background
            bg_rgb = tuple(int(_BG[i:i + 2], 16) for i in (1, 3, 5))
            display = Image.new("RGBA", img.size, bg_rgb + (255,))
            display.paste(img, mask=img.split()[3])

            photo = ImageTk.PhotoImage(display)
            cv._logo = photo
            cv.create_image(self._W // 2, cy, image=photo, anchor=tk.CENTER)
            return cy + img.height // 2
        except Exception:  # pylint: disable=broad-except
            return cy

    def _draw_text(self, cv: tk.Canvas, logo_bottom: int):
        cx      = self._W // 2
        title_y = max(logo_bottom + self._s(28), self._s(220))

        cv.create_text(cx, title_y, text="InoLabel",
                       fill=_WHITE,
                       font=self._f("Helvetica", 36, "bold"),
                       anchor=tk.CENTER)

        sub_y = title_y + self._s(46)
        cv.create_text(cx, sub_y,
                       text="Laboratório de Visão Computacional  ·  Inovisão",
                       fill=_MUTED,
                       font=self._f("Helvetica", 13),
                       anchor=tk.CENTER)

        line_y = sub_y + self._s(24)
        half   = self._s(40)
        cv.create_line(cx - half, line_y, cx + half, line_y, fill=_ORANGE, width=2)

    def _draw_button(self, cv: tk.Canvas):
        btn = _RoundedButton(
            self.root, "Começar  →", self._start,
            radius=self._s(10),
            bg=_BLUE, hover_bg=_ORANGE,
            fg=_WHITE,
            font=self._f("Helvetica", 14, "bold"),
            padx=self._s(52), pady=self._s(16),
        )
        cv.create_window(self._W // 2, self._H - self._s(80),
                         window=btn, anchor=tk.CENTER)

    def _draw_footer(self, cv: tk.Canvas):
        cv.create_text(self._W // 2, self._H - self._s(22),
                       text="Pressione Enter ou clique em Começar",
                       fill=_BORDER,
                       font=self._f("Helvetica", 10),
                       anchor=tk.CENTER)

    # ── actions ───────────────────────────────────────────────────

    def _start(self):
        self._started = True
        self.root.destroy()

    def _close(self):
        self._started = False
        self.root.destroy()

    def run(self) -> bool:
        self.root.mainloop()
        return self._started


def show_intro() -> bool:
    """Show intro screen; return True if user clicked Começar, False if closed."""
    return IntroScreen().run()
