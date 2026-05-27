"""Editor visual de keybinds estilo Valorant para o InoLabel."""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog
from typing import Dict, Optional

from app.annotation.keybinds.actions import ACTION_REGISTRY, ActionDescriptor
from app.annotation.keybinds.keybind_map import KeybindMap
from app.annotation.keybinds.keybind_repository import KeybindRepository
from app.annotation.keybinds.keybind_service import KeybindService, MODIFIER_KEYSYMS
from app.ui.components import make_btn
from app.ui.theme.tokens import COLORS, FONTS, SPACING

# ── conversão de tecla para texto legível ─────────────────────────────────────

_KEY_DISPLAY: Dict[str, str] = {
    "Right": "→",
    "Left": "←",
    "Up": "↑",
    "Down": "↓",
    "Return": "Enter",
    "space": "Espaço",
    "BackSpace": "Backspace",
    "Delete": "Delete",
    "Tab": "Tab",
    "Control-z": "Ctrl+Z",
    "Control-Z": "Ctrl+Z",
    "Control-0": "Ctrl+0",
    "Control-c": "Ctrl+C",
    "Control-v": "Ctrl+V",
    "": "(sem bind)",
}


def _display_key(key: str) -> str:
    if key in _KEY_DISPLAY:
        return _KEY_DISPLAY[key]
    # modifier combos genericos: Control-x → Ctrl+X
    if "-" in key and not key.startswith("<"):
        mod, rest = key.split("-", 1)
        mod_map = {"Control": "Ctrl", "Shift": "Shift", "Alt": "Alt"}
        mod_label = mod_map.get(mod, mod)
        return f"{mod_label}+{rest.upper()}"
    return key.upper() if len(key) == 1 else key


def _parse_event_key(event) -> Optional[str]:
    """Converte um evento KeyPress para string interna (ex: 'Right', 'd', 'Control-z')."""
    keysym = event.keysym
    if keysym in MODIFIER_KEYSYMS or keysym == "Escape":
        return None  # ignorar; Escape cancela captura

    state = event.state
    ctrl = bool(state & 0x4)

    if ctrl:
        char = keysym.lower()
        return f"Control-{char}"

    # Teclas especiais
    if keysym in {
        "Right", "Left", "Up", "Down",
        "Return", "space", "BackSpace", "Delete", "Tab",
        "Home", "End", "Prior", "Next", "Insert",
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
    }:
        return keysym

    # Caracter imprimível
    char = event.char
    if char and char.isprintable():
        return char.lower()

    return keysym.lower() if keysym else None


# ── janela do editor ──────────────────────────────────────────────────────────

class KeybindEditorWindow:
    def __init__(self, parent: tk.Misc, service: KeybindService, tool):
        self._service = service
        self._tool = tool
        self._listening_action: Optional[str] = None
        self._listening_btn: Optional[tk.Button] = None
        self._edit_profile: Optional[KeybindMap] = None
        self._row_widgets: Dict[str, tk.Button] = {}  # action_id → key button
        self._conflict_label: Optional[tk.Label] = None

        self._win = tk.Toplevel(parent)
        self._win.title("Configurar atalhos de teclado")
        self._win.configure(bg=COLORS["panel"])
        self._win.resizable(False, False)
        self._win.transient(parent)
        self._win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._win.geometry("680x560")
        self._win.minsize(680, 480)

        self._build()
        self._win.lift()
        self._win.focus_force()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = tk.Frame(self._win, bg=COLORS["panel"])
        root.pack(fill=tk.BOTH, expand=True, padx=SPACING["md"], pady=SPACING["md"])

        # ── header ───────────────────────────────────────────────────────────
        header = tk.Frame(root, bg=COLORS["panel"])
        header.pack(fill=tk.X, pady=(0, SPACING["sm"]))

        tk.Label(
            header,
            text="Configurar atalhos de teclado",
            font=FONTS["heading"],
            bg=COLORS["panel"],
            fg=COLORS["text"],
            anchor="w",
        ).pack(side=tk.LEFT)

        # ── profile row ──────────────────────────────────────────────────────
        profile_row = tk.Frame(root, bg=COLORS["panel"])
        profile_row.pack(fill=tk.X, pady=(0, SPACING["sm"]))

        tk.Label(
            profile_row,
            text="Perfil:",
            font=FONTS["label"],
            bg=COLORS["panel"],
            fg=COLORS["text"],
        ).pack(side=tk.LEFT, padx=(0, SPACING["xs"]))

        self._profile_var = tk.StringVar()
        profiles = list(self._service.get_profiles().keys())
        active = self._service.get_active_profile_name()
        self._profile_var.set(active)

        self._profile_menu = tk.OptionMenu(
            profile_row,
            self._profile_var,
            *profiles,
            command=self._on_profile_change,
        )
        self._profile_menu.config(
            font=FONTS["body"],
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            activebackground=COLORS["neutral_active"],
            cursor="hand2",
        )
        self._profile_menu["menu"].config(
            font=FONTS["body"],
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["primary"],
            activeforeground=COLORS["fg_light"],
        )
        self._profile_menu.pack(side=tk.LEFT, padx=(0, SPACING["xs"]))

        make_btn(
            profile_row, "+ Novo", self._on_new_profile, variant="neutral", size="sm"
        ).pack(side=tk.LEFT, padx=(0, SPACING["xs"]))

        self._delete_btn = make_btn(
            profile_row, "Deletar", self._on_delete_profile, variant="danger", size="sm"
        )
        self._delete_btn.pack(side=tk.LEFT)
        self._update_delete_btn()

        # ── scrollable action list ────────────────────────────────────────────
        list_frame = tk.Frame(root, bg=COLORS["panel"])
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING["xs"]))

        canvas = tk.Canvas(list_frame, bg=COLORS["panel"], bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._actions_frame = tk.Frame(canvas, bg=COLORS["panel"])
        self._canvas_window = canvas.create_window((0, 0), window=self._actions_frame, anchor="nw")

        def _on_frame_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(self._canvas_window, width=event.width)

        self._actions_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))
        canvas.bind("<Button-4>", lambda _: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda _: canvas.yview_scroll(1, "units"))

        self._rebuild_action_rows()

        # ── conflict / status label ───────────────────────────────────────────
        self._conflict_var = tk.StringVar()
        self._conflict_label = tk.Label(
            root,
            textvariable=self._conflict_var,
            font=FONTS["caption"],
            bg=COLORS["panel"],
            fg=COLORS["accent"],
            anchor="w",
            justify=tk.LEFT,
        )
        self._conflict_label.pack(fill=tk.X, pady=(SPACING["xs"], 0))

        # ── footer ────────────────────────────────────────────────────────────
        footer = tk.Frame(root, bg=COLORS["panel"])
        footer.pack(fill=tk.X, pady=(SPACING["sm"], 0))
        footer.grid_columnconfigure(0, weight=1)

        make_btn(
            footer, "Restaurar padrões", self._on_reset_defaults, variant="neutral", size="sm"
        ).grid(row=0, column=0, sticky="w")

        make_btn(
            footer, "Fechar", self._on_close, variant="neutral", size="sm"
        ).grid(row=0, column=2, sticky="e", padx=(SPACING["xs"], 0))

        make_btn(
            footer, "Aplicar", self._on_apply, variant="primary", size="sm"
        ).grid(row=0, column=1, sticky="e", padx=(0, SPACING["xs"]))

        # captura de tecla na janela
        self._win.bind("<KeyPress>", self._on_key_press)
        # cancelar captura ao clicar fora
        self._win.bind("<ButtonPress-1>", self._on_click_outside)

    # ── action rows ───────────────────────────────────────────────────────────

    def _rebuild_action_rows(self) -> None:
        for widget in self._actions_frame.winfo_children():
            widget.destroy()
        self._row_widgets.clear()

        profile = self._get_edit_profile()
        tracking_enabled = getattr(self._tool, "tracking_enabled", False)
        is_obb = not tracking_enabled and not getattr(self._tool, "session_config", None) or True
        # check mode more precisely
        task_mode = getattr(getattr(self._tool, "session_config", None), "mode", None)
        mode_value = task_mode.value if task_mode else "tracking"

        current_group = None
        row = 0

        visible_actions = [
            a for a in ACTION_REGISTRY
            if not (a.tracking_only and not tracking_enabled)
            and not (not a.obb and mode_value == "obb")
        ]

        for action in visible_actions:
            if action.group != current_group:
                current_group = action.group
                if row > 0:
                    # separator
                    tk.Frame(self._actions_frame, bg=COLORS["border"], height=1).grid(
                        row=row, column=0, columnspan=2, sticky="ew", pady=(SPACING["xs"], 0)
                    )
                    row += 1
                tk.Label(
                    self._actions_frame,
                    text=current_group.upper(),
                    font=FONTS["tag"],
                    bg=COLORS["panel"],
                    fg=COLORS["muted"],
                    anchor="w",
                    pady=SPACING["xs"],
                ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=SPACING["xs"])
                row += 1

            self._build_action_row(action, profile, row)
            row += 1

        self._actions_frame.grid_columnconfigure(0, weight=1)
        self._actions_frame.grid_columnconfigure(1, minsize=120)

    def _build_action_row(self, action: ActionDescriptor, profile: KeybindMap, row: int) -> None:
        is_even = row % 2 == 0
        bg = COLORS["panel_alt"] if is_even else COLORS["panel"]

        label = tk.Label(
            self._actions_frame,
            text=f"  {action.label}",
            font=FONTS["body"],
            bg=bg,
            fg=COLORS["text"],
            anchor="w",
            pady=6,
        )
        label.grid(row=row, column=0, sticky="ew", padx=(SPACING["xs"], 0))

        key = profile.get_key(action.id) or ""
        btn = tk.Button(
            self._actions_frame,
            text=_display_key(key),
            font=FONTS["body"],
            bg=bg,
            fg=COLORS["text"],
            relief=tk.FLAT,
            bd=0,
            pady=6,
            padx=SPACING["sm"],
            cursor="hand2",
            width=12,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            activebackground=COLORS["neutral_active"],
            activeforeground=COLORS["text"],
        )
        btn.grid(row=row, column=1, sticky="ew", padx=SPACING["xs"], pady=1)

        action_id = action.id
        btn.config(command=lambda a=action_id, b=btn: self._start_listening(a, b))
        self._row_widgets[action_id] = btn

    # ── listening (captura de tecla) ─────────────────────────────────────────

    def _start_listening(self, action_id: str, btn: tk.Button) -> None:
        self._cancel_listening()
        self._listening_action = action_id
        self._listening_btn = btn
        btn.config(
            text="...",
            bg=COLORS["primary"],
            fg=COLORS["fg_light"],
            relief=tk.FLAT,
        )
        self._conflict_var.set("")
        self._win.focus_set()

    def _cancel_listening(self) -> None:
        if self._listening_btn is not None:
            profile = self._get_edit_profile()
            key = profile.get_key(self._listening_action or "") or ""
            self._listening_btn.config(
                text=_display_key(key),
                bg=COLORS["panel_alt"] if self._row_bg_even(self._listening_action) else COLORS["panel"],
                fg=COLORS["text"],
                relief=tk.FLAT,
            )
        self._listening_action = None
        self._listening_btn = None

    def _row_bg_even(self, action_id: Optional[str]) -> bool:
        if action_id is None:
            return True
        visible = [
            a for a in ACTION_REGISTRY
            if not (a.tracking_only and not getattr(self._tool, "tracking_enabled", False))
        ]
        idx = next((i for i, a in enumerate(visible) if a.id == action_id), 0)
        return idx % 2 == 0

    def _on_key_press(self, event) -> None:
        if self._listening_action is None:
            return
        if event.keysym == "Escape":
            self._cancel_listening()
            return
        key = _parse_event_key(event)
        if key is None:
            return

        profile = self._get_edit_profile()
        conflict = profile.conflicts_with(key, self._listening_action)
        if conflict:
            conflict_label = next(
                (a.label for a in ACTION_REGISTRY if a.id == conflict), conflict
            )
            self._conflict_var.set(f'⚠  "{_display_key(key)}" já está em uso por "{conflict_label}"')
        else:
            self._conflict_var.set("")

        profile.set_key(self._listening_action, key)
        btn = self._listening_btn
        action_id = self._listening_action
        self._listening_action = None
        self._listening_btn = None

        if btn is not None:
            btn.config(
                text=_display_key(key),
                bg=COLORS["panel_alt"] if self._row_bg_even(action_id) else COLORS["panel"],
                fg=COLORS["text"],
            )

    def _on_click_outside(self, event) -> None:
        if self._listening_btn is not None and event.widget is not self._listening_btn:
            self._cancel_listening()

    # ── profile management ────────────────────────────────────────────────────

    def _get_edit_profile(self) -> KeybindMap:
        name = self._profile_var.get()
        profiles = self._service.get_profiles()
        if self._edit_profile is None or self._edit_profile.name != name:
            source = profiles.get(name, profiles.get("arrows"))
            self._edit_profile = source.copy() if source else KeybindMap(name=name)
            self._edit_profile.name = name
        return self._edit_profile

    def _on_profile_change(self, name: str) -> None:
        self._cancel_listening()
        self._edit_profile = None
        self._conflict_var.set("")
        self._update_delete_btn()
        self._rebuild_action_rows()

    def _on_new_profile(self) -> None:
        name = simpledialog.askstring(
            "Novo perfil",
            "Nome do novo perfil:",
            parent=self._win,
        )
        if not name or not name.strip():
            return
        name = name.strip()
        if name in self._service.get_profiles():
            self._conflict_var.set(f'⚠  Perfil "{name}" já existe.')
            return
        self._service.add_profile(name, base_name=self._profile_var.get())
        self._profile_var.set(name)
        self._edit_profile = None
        self._refresh_profile_menu()
        self._update_delete_btn()
        self._rebuild_action_rows()

    def _on_delete_profile(self) -> None:
        name = self._profile_var.get()
        if KeybindRepository.is_builtin(name):
            return
        self._service.delete_profile(name)
        self._profile_var.set("arrows")
        self._edit_profile = None
        self._refresh_profile_menu()
        self._update_delete_btn()
        self._rebuild_action_rows()

    def _refresh_profile_menu(self) -> None:
        menu = self._profile_menu["menu"]
        menu.delete(0, tk.END)
        for pname in self._service.get_profiles():
            menu.add_command(
                label=pname,
                command=lambda n=pname: (self._profile_var.set(n), self._on_profile_change(n)),
            )

    def _update_delete_btn(self) -> None:
        name = self._profile_var.get()
        state = tk.DISABLED if KeybindRepository.is_builtin(name) else tk.NORMAL
        self._delete_btn.config(state=state)

    # ── footer actions ────────────────────────────────────────────────────────

    def _on_reset_defaults(self) -> None:
        name = self._profile_var.get()
        self._edit_profile = None
        self._service.reset_profile_to_defaults(name)
        self._conflict_var.set("")
        self._rebuild_action_rows()

    def _on_apply(self) -> None:
        profile = self._get_edit_profile()
        self._service.save_profile(profile)
        self._service.apply_profile(profile.name)
        if hasattr(self._tool, "update_key_mapping_button"):
            self._tool.update_key_mapping_button()
        self._conflict_var.set("✓  Atalhos aplicados.")
        self._profile_var.set(profile.name)
        self._refresh_profile_menu()

    def _on_close(self) -> None:
        self._cancel_listening()
        if hasattr(self._tool, "_keybind_editor_window"):
            self._tool._keybind_editor_window = None
        try:
            self._win.destroy()
        except Exception:  # pylint: disable=broad-except
            pass

    def lift(self) -> None:
        self._win.lift()

    def focus_force(self) -> None:
        self._win.focus_force()
