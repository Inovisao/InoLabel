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
    annotate = ROOT / "frontend" / "src" / "features" / "annotate"
    topbar = (annotate / "Topbar.tsx").read_text(encoding="utf-8")
    sidebar = (annotate / "sidebar" / "Sidebar.tsx").read_text(encoding="utf-8")
    statusbar = (annotate / "Statusbar.tsx").read_text(encoding="utf-8")

    assert 'height: 56' in topbar
    assert 'width: 320' in sidebar
    assert 'height: 40' in statusbar
    assert "framer-motion" not in topbar
    assert "framer-motion" not in sidebar
    assert "letterSpacing: \"-0.02em\"" not in topbar


def test_react_canvas_uses_stroked_overlays_without_tint_fill():
    canvas_dir = ROOT / "frontend" / "src" / "features" / "annotate" / "canvas"
    # As formas ficam em componentes próprios (BoxShape, ObbShape...): confere a pasta toda.
    canvas = "\n".join(f.read_text(encoding="utf-8") for f in sorted(canvas_dir.glob("*.tsx")))

    assert 'background: "var(--color-canvas-bg)"' in canvas
    assert "strokeWidth={2}" in canvas
    assert "fill={`${clsColor}18`}" not in canvas
    assert "fill={`${color}18`}" not in canvas
