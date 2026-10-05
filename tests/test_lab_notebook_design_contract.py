from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_react_styles_use_lab_notebook_tokens():
    css = (ROOT / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")

    for token in (
        "--color-bg: #F0F4FA",
        "--color-panel: #FFFFFF",
        "--color-panel-alt: #EEF3FB",
        "--color-border: #C2D0E8",
        "--color-text: #152040",
        "--color-muted: #526A88",
        "--color-primary: #1560BD",
        "--color-primary-active: #0D47A1",
        "--color-accent: #F07820",
        "--color-canvas-bg: #16130f",
        '--font-sans: Helvetica, Arial, sans-serif',
        '--font-mono: Courier, monospace',
    ):
        assert token in css

    assert "--color-amber" not in css
    assert "Inter" not in css
    assert "JetBrains Mono" not in css
    assert "gradient" not in css.lower()


def test_react_layout_matches_lab_notebook_shell():
    topbar = (ROOT / "frontend" / "src" / "components" / "layout" / "Topbar.tsx").read_text(encoding="utf-8")
    sidebar = (ROOT / "frontend" / "src" / "components" / "layout" / "Sidebar.tsx").read_text(encoding="utf-8")
    statusbar = (ROOT / "frontend" / "src" / "components" / "layout" / "Statusbar.tsx").read_text(encoding="utf-8")

    assert 'height: 56' in topbar
    assert 'width: 320' in sidebar
    assert 'height: 40' in statusbar
    assert "framer-motion" not in topbar
    assert "framer-motion" not in sidebar
    assert "letterSpacing: \"-0.02em\"" not in topbar


def test_react_canvas_uses_stroked_overlays_without_tint_fill():
    canvas = (ROOT / "frontend" / "src" / "components" / "canvas" / "AnnotationCanvas.tsx").read_text(encoding="utf-8")

    assert 'background: "var(--color-canvas-bg)"' in canvas
    assert "strokeWidth={2}" in canvas
    assert "fill={`${clsColor}18`}" not in canvas
    assert "fill={`${color}18`}" not in canvas


def test_python_canvas_overlay_colors_are_tokenized():
    from app.annotation.ui import display_overlays

    assert display_overlays.ROI_LINE_COLOR == "#1560BD"
    assert display_overlays.ROI_POINT_COLOR == "#F07820"
    assert display_overlays.MANUAL_RECTANGLE_COLOR == "#F07820"
