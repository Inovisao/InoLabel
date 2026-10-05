import json
import tempfile
import threading
import tkinter as tk
import unittest
from pathlib import Path

from app.annotation.infrastructure.persistence.async_writer import AnnotationsAsyncWriterMixin
from app.annotation.ui.display_canvas import DisplayCanvasMixin


class _Writer(AnnotationsAsyncWriterMixin):
    def __init__(self, path: Path):
        self.annotations_path = path


class AnnotationsWriterOrderingTest(unittest.TestCase):
    def test_blocking_write_concurrent_with_background_write_does_not_fail(self):
        # Reproduces the export failure: autosave queues a background write and the export
        # thread immediately does a blocking write to the same file.
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer = _Writer(Path(tmp_dir) / "annotations.coco.json")
            errors = []

            def blocking_writes():
                try:
                    for i in range(50):
                        writer._write_annotations_now({"v": 1000 + i})
                except Exception as exc:  # pylint: disable=broad-except
                    errors.append(exc)

            for i in range(50):
                writer._queue_annotations_write({"v": i})
            thread = threading.Thread(target=blocking_writes)
            thread.start()
            for i in range(50, 100):
                writer._queue_annotations_write({"v": i})
            thread.join()
            writer.flush_pending_annotations()

            self.assertEqual(errors, [])
            self.assertFalse(writer.annotations_path.with_name("annotations.coco.json.tmp").exists())
            json.loads(writer.annotations_path.read_text(encoding="utf-8"))

    def test_older_snapshot_never_overwrites_newer_one(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer = _Writer(Path(tmp_dir) / "annotations.coco.json")
            writer._ensure_annotations_writer_state()
            with writer._annotations_writer_lock:
                old_seq = writer._next_annotations_seq()

            writer._write_annotations_now({"state": "new"})
            # The background writer finishing late with the older snapshot.
            writer._flush_annotations({"state": "old"}, old_seq)

            data = json.loads(writer.annotations_path.read_text(encoding="utf-8"))
            self.assertEqual(data, {"state": "new"})

    def test_blocking_write_drops_superseded_queued_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            writer = _Writer(Path(tmp_dir) / "annotations.coco.json")
            writer._ensure_annotations_writer_state()
            with writer._annotations_writer_lock:
                writer._annotations_pending_payload = (writer._next_annotations_seq(), {"state": "old"})

            writer._write_annotations_now({"state": "new"})
            writer.flush_pending_annotations()

            data = json.loads(writer.annotations_path.read_text(encoding="utf-8"))
            self.assertEqual(data, {"state": "new"})


class CanvasAliveTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk indisponivel: {exc}")
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def _display(self, canvas):
        display = DisplayCanvasMixin()
        display.canvas = canvas
        display.export_screen_active = False
        return display

    def test_destroyed_canvas_is_not_alive(self):
        canvas = tk.Canvas(self.root)
        display = self._display(canvas)
        self.assertTrue(display._canvas_alive())

        canvas.destroy()

        self.assertFalse(display._canvas_alive())

    def test_export_screen_blocks_redraw(self):
        display = self._display(tk.Canvas(self.root))
        display.export_screen_active = True
        self.assertFalse(display._canvas_alive())

    def test_update_display_skips_destroyed_canvas(self):
        canvas = tk.Canvas(self.root)
        display = self._display(canvas)
        display.current_frame = object()
        canvas.destroy()

        display.update_display(refresh_status=True)  # must not raise TclError


if __name__ == "__main__":
    unittest.main()
