"""Entry point Flet — exibe wizard de inicialização e lança a ferramenta correta."""

from __future__ import annotations

import sys
from typing import Optional

import flet as ft

from app.core.session import AnnotationSessionConfig, AnnotationTaskMode
from app.ui.startup.flet_wizard import ask_startup_config_flet


def _configure_page(page: ft.Page) -> None:
    page.title = "InoLabel"
    page.bgcolor = "#F7F9FC"
    page.padding = 0
    page.spacing = 0
    page.window.min_width = 900
    page.window.min_height = 600
    page.fonts = {}
    page.theme = ft.Theme(
        color_scheme_seed="#2563EB",
        use_material3=True,
    )


def _on_wizard_complete(page: ft.Page, config: Optional[AnnotationSessionConfig]) -> None:
    if config is None:
        page.window.close()
        return

    page.controls.clear()
    page.update()

    tool = None
    try:
        if config.mode is AnnotationTaskMode.CLASSIFICATION:
            from app.classification.flet_tool import FletClassificationTool  # pylint: disable=import-outside-toplevel
            tool = FletClassificationTool(session_config=config, page=page)
        elif config.mode is AnnotationTaskMode.OBB:
            from app.annotation_obb.flet_tool import FletOBBAnnotationTool  # pylint: disable=import-outside-toplevel
            tool = FletOBBAnnotationTool(session_config=config, page=page)
        else:
            from app.annotation.flet_tool import FletAnnotationTool  # pylint: disable=import-outside-toplevel
            tool = FletAnnotationTool(session_config=config, page=page)

        tool.run()

    except KeyboardInterrupt:
        if tool is not None:
            tool.finish_processing("Interrompido.")
        page.window.close()
    except Exception as exc:  # pylint: disable=broad-except
        if tool is not None:
            tool.finish_processing(f"Erro: {exc}")
        print(f"[ERRO] {exc}", file=sys.stderr)
        import traceback  # pylint: disable=import-outside-toplevel
        traceback.print_exc()


def main() -> int:
    def flet_main(page: ft.Page) -> None:
        _configure_page(page)
        ask_startup_config_flet(
            page,
            on_complete=lambda config: _on_wizard_complete(page, config),
        )

    ft.app(target=flet_main)
    return 0
