from unittest.mock import patch

import main


def test_missing_frontend_reports_build_steps(tmp_path, capsys):
    with patch.object(main.sys, "_MEIPASS", str(tmp_path), create=True):
        assert not main._frontend_ready(False)
    assert "npm run build" in capsys.readouterr().err


def test_compiled_frontend_is_ready(tmp_path):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")
    with patch.object(main.sys, "_MEIPASS", str(tmp_path), create=True):
        assert main._frontend_ready(False)


def test_development_does_not_require_compiled_frontend():
    assert main._frontend_ready(True)


def test_browser_opens_development_frontend_after_api_is_ready():
    with patch.object(main.urllib.request, "urlopen"), patch.object(main.webbrowser, "open") as browser:
        main._open_browser("http://localhost:5173")
    browser.assert_called_once_with("http://localhost:5173")


def test_browser_stays_closed_when_api_times_out():
    with patch.object(main.time, "monotonic", side_effect=[0, 31]), patch.object(main.webbrowser, "open") as browser:
        main._open_browser()
    browser.assert_not_called()
