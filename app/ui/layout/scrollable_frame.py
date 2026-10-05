"""A simple vertical scrollable frame for Tk screens."""

from __future__ import annotations

import tkinter as tk


class ScrollableFrame(tk.Frame):
    """Frame with vertical scrolling that adapts to its parent width.

    O scroll do mouse funciona mesmo quando o cursor está sobre widgets
    filhos (cards, sliders, labels): ao entrar no frame, o binding é
    ativado globalmente na toplevel; ao sair, é removido.
    """

    def __init__(self, parent, *, bg: str):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=bg)
        self._window_id = self.canvas.create_window((0, 0), window=self.content, anchor=tk.NW)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Ativa scroll global ao entrar; remove ao sair — cobre todos os filhos
        self.bind("<Enter>", self._grab_scroll)
        self.bind("<Leave>", self._release_scroll)

    # ── layout ────────────────────────────────────────────────────────────────

    def _on_content_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._window_id, width=event.width)

    # ── scroll ────────────────────────────────────────────────────────────────

    def _on_mousewheel(self, event):
        delta = getattr(event, "delta", 0)
        num = getattr(event, "num", None)
        if delta:
            self.canvas.yview_scroll(int(-1 * delta / 120), "units")
        elif num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif num == 5:
            self.canvas.yview_scroll(1, "units")

    def _grab_scroll(self, _event=None):
        top = self.winfo_toplevel()
        top.bind_all("<MouseWheel>", self._on_mousewheel)
        top.bind_all("<Button-4>", self._on_mousewheel)
        top.bind_all("<Button-5>", self._on_mousewheel)

    def _release_scroll(self, _event=None):
        top = self.winfo_toplevel()
        top.unbind_all("<MouseWheel>")
        top.unbind_all("<Button-4>")
        top.unbind_all("<Button-5>")

    def bind_mousewheel_to(self, widget: tk.Widget) -> None:
        """Registra manualmente o scroll de um widget externo no canvas."""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)
        widget.bind("<Button-5>", self._on_mousewheel)
