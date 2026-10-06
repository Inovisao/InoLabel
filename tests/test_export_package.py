"""Exportação zipada: referências conferidas e pacote portátil."""

import asyncio
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.annotation.infrastructure.export.export_dir import EXPORT_MARKER
from app.core.export_package import (
    BrokenDatasetLinksError,
    portable_data_yaml,
    verify_dataset_links,
    zip_dataset,
)


def _image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((10, 12, 3), dtype=np.uint8))


def _yolo_dataset(root: Path, names=("a", "b")) -> Path:
    for name in names:
        _image(root / "images" / "train" / f"{name}.jpg")
        label = root / "labels" / "train" / f"{name}.txt"
        label.parent.mkdir(parents=True, exist_ok=True)
        label.write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (root / "data.yaml").write_text(
        f"path: {root.resolve()}\ntrain: images/train\n\nnames:\n  0: car\n", encoding="utf-8"
    )
    (root / EXPORT_MARKER).write_text("x", encoding="utf-8")
    return root


def _coco_dataset(root: Path) -> Path:
    _image(root / "images" / "a.jpg")
    payload = {
        "images": [{"id": 1, "file_name": "a.jpg", "width": 12, "height": 10}],
        "annotations": [{"id": 1, "image_id": 1, "category_id": 0, "bbox": [1, 1, 4, 4]}],
        "categories": [{"id": 0, "name": "car"}],
    }
    (root / "_annotations.coco.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


# ── verify_dataset_links ─────────────────────────────────────────────────────

def test_consistent_yolo_dataset_passes(tmp_path):
    report = verify_dataset_links(_yolo_dataset(tmp_path / "ds"))
    assert report["yolo_images"] == 2
    assert report["yolo_labels"] == 2


def test_yolo_image_without_label_is_reported(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")
    (root / "labels" / "train" / "b.txt").unlink()
    with pytest.raises(BrokenDatasetLinksError) as exc:
        verify_dataset_links(root)
    assert any("imagem sem label" in p and "train/b" in p for p in exc.value.problems)


def test_yolo_label_without_image_is_reported(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")
    (root / "images" / "train" / "a.jpg").unlink()
    with pytest.raises(BrokenDatasetLinksError) as exc:
        verify_dataset_links(root)
    assert any("label sem imagem" in p for p in exc.value.problems)


def test_yolo_without_data_yaml_is_reported(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")
    (root / "data.yaml").unlink()
    with pytest.raises(BrokenDatasetLinksError):
        verify_dataset_links(root)


def test_consistent_coco_dataset_passes(tmp_path):
    report = verify_dataset_links(_coco_dataset(tmp_path / "ds"))
    assert report["coco_files"] == 1
    assert report["coco_images"] == 1
    assert report["coco_annotations"] == 1


def test_coco_from_older_exports_is_still_checked(tmp_path):
    """Exportações anteriores gravavam annotations.json."""
    root = _coco_dataset(tmp_path / "ds")
    (root / "_annotations.coco.json").rename(root / "annotations.json")
    assert verify_dataset_links(root)["coco_files"] == 1


def test_coco_pointing_to_missing_image_is_reported(tmp_path):
    root = _coco_dataset(tmp_path / "ds")
    (root / "images" / "a.jpg").unlink()
    with pytest.raises(BrokenDatasetLinksError) as exc:
        verify_dataset_links(root)
    assert any("imagem ausente" in p for p in exc.value.problems)


def test_coco_annotation_with_unknown_image_or_category_is_reported(tmp_path):
    root = _coco_dataset(tmp_path / "ds")
    data = json.loads((root / "_annotations.coco.json").read_text(encoding="utf-8"))
    data["annotations"].append({"id": 2, "image_id": 99, "category_id": 7, "bbox": [0, 0, 1, 1]})
    (root / "_annotations.coco.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(BrokenDatasetLinksError) as exc:
        verify_dataset_links(root)
    problems = " | ".join(exc.value.problems)
    assert "sem imagem correspondente" in problems
    assert "categoria inexistente" in problems


def test_empty_folder_is_not_a_dataset(tmp_path):
    (tmp_path / "ds").mkdir()
    with pytest.raises(BrokenDatasetLinksError):
        verify_dataset_links(tmp_path / "ds")


# ── zip_dataset ──────────────────────────────────────────────────────────────

def test_zip_has_single_root_folder_with_images_and_labels(tmp_path):
    root = _yolo_dataset(tmp_path / "meu_dataset")

    zip_path = zip_dataset(root)

    assert zip_path == tmp_path / "meu_dataset.zip"
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert names == {
        "meu_dataset/data.yaml",
        "meu_dataset/images/train/a.jpg",
        "meu_dataset/images/train/b.jpg",
        "meu_dataset/labels/train/a.txt",
        "meu_dataset/labels/train/b.txt",
    }


def test_zipped_data_yaml_has_no_machine_path_but_folder_copy_keeps_it(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")

    zip_path = zip_dataset(root)

    with zipfile.ZipFile(zip_path) as archive:
        zipped_yaml = archive.read("ds/data.yaml").decode("utf-8")
    assert "path:" not in zipped_yaml
    assert str(tmp_path) not in zipped_yaml
    assert "train: images/train" in zipped_yaml
    assert "path:" in (root / "data.yaml").read_text(encoding="utf-8")


def test_extracted_package_still_verifies_elsewhere(tmp_path):
    """Extraído em outra pasta, o dataset continua com todas as referências válidas."""
    yolo_zip = zip_dataset(_yolo_dataset(tmp_path / "yolo_ds"))
    coco_zip = zip_dataset(_coco_dataset(tmp_path / "coco_ds"))
    elsewhere = tmp_path / "outra_maquina"
    for archive_path in (yolo_zip, coco_zip):
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(elsewhere)
    shutil.rmtree(tmp_path / "yolo_ds")
    shutil.rmtree(tmp_path / "coco_ds")

    assert verify_dataset_links(elsewhere / "yolo_ds")["yolo_images"] == 2
    assert verify_dataset_links(elsewhere / "coco_ds")["coco_images"] == 1


def test_zip_replaces_previous_archive_and_leaves_no_tmp(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")
    zip_dataset(root)
    _image(root / "images" / "train" / "c.jpg")
    (root / "labels" / "train" / "c.txt").write_text("", encoding="utf-8")

    zip_path = zip_dataset(root)

    with zipfile.ZipFile(zip_path) as archive:
        assert "ds/images/train/c.jpg" in archive.namelist()
    assert not list(tmp_path.glob("*.tmp"))


def test_zip_reports_progress(tmp_path):
    root = _yolo_dataset(tmp_path / "ds")
    seen = []
    zip_dataset(root, on_progress=lambda done, total, name: seen.append((done, total)))
    assert seen[-1] == (5, 5)


def test_portable_data_yaml_only_drops_path_line():
    text = "path: /home/x/ds\ntrain: images/train\n\nnames:\n  0: car\n"
    assert portable_data_yaml(text) == "train: images/train\n\nnames:\n  0: car\n"


# ── fluxo completo pela API ──────────────────────────────────────────────────

@pytest.fixture()
def session_with_frames():
    from app.api.common.schemas import Annotation
    from app.api.state import (
        annotation_store, create_session, frame_dims, frame_paths, next_ann_id, reset_state,
    )

    tmp = Path(tempfile.mkdtemp())
    reset_state()
    data = tmp / "dataset"
    create_session(mode="detection", data_path=data, output_path=tmp / "projeto", classes=["car"])
    for i in range(3):
        img_path = data / f"frame_{i:03d}.jpg"
        _image(img_path)
        frame_paths.append(img_path)
        frame_dims[i] = (12, 10)
        annotation_store[i] = [
            Annotation(id=next_ann_id[0], image_id=i, category_id=0, bbox=[1.0, 1.0, 5.0, 4.0])
        ]
        next_ann_id[0] += 1
    yield tmp
    reset_state()
    shutil.rmtree(tmp, ignore_errors=True)


def _export(tmp: Path, name: str, formats, *, use_split=False, zip_output=True):
    from app.api.export.service import run_export
    from app.api.state import create_export
    from app.core.exporter import ExportJob

    job = create_export(ExportJob(
        destination=tmp / "exports", name=name, formats=formats,
        use_split=use_split, zip_output=zip_output,
    ))
    asyncio.run(run_export(job.export_id))
    return job


@pytest.mark.parametrize("formats,use_split", [(["yolo"], False), (["yolo"], True), (["coco"], False), (["coco"], True)])
def test_api_export_zipped_is_self_contained(session_with_frames, formats, use_split):
    tmp = session_with_frames

    job = _export(tmp, "ds", formats, use_split=use_split)

    assert job.status == "done", job.current_file
    assert job.zip_path == tmp / "exports" / "ds.zip"
    elsewhere = tmp / "outra_maquina"
    with zipfile.ZipFile(job.zip_path) as archive:
        archive.extractall(elsewhere)
        image_entries = [n for n in archive.namelist() if n.endswith(".jpg")]
    assert len(image_entries) == 3
    verify_dataset_links(elsewhere / "ds")


def test_api_export_without_zip_creates_no_archive(session_with_frames):
    tmp = session_with_frames
    job = _export(tmp, "ds", ["yolo"], zip_output=False)
    assert job.status == "done", job.current_file
    assert job.zip_path is None
    assert not (tmp / "exports" / "ds.zip").exists()


def test_api_export_fails_without_zip_when_links_are_broken(session_with_frames, monkeypatch):
    """Referência quebrada interrompe a exportação: nenhum zip incompleto é entregue."""
    tmp = session_with_frames
    from app.annotation.infrastructure.export import yolo_exporter

    original = yolo_exporter.export_yolo_no_split

    def export_then_lose_a_label(*args, **kwargs):
        report = original(*args, **kwargs)
        next((kwargs["dataset_root"] / "labels" / "all").glob("*.txt")).unlink()
        return report

    monkeypatch.setattr(yolo_exporter, "export_yolo_no_split", export_then_lose_a_label)

    job = _export(tmp, "ds", ["yolo"])

    assert job.status == "error"
    assert "referências quebradas" in job.current_file
    assert not (tmp / "exports" / "ds.zip").exists()


def test_export_request_accepts_zip_flag_and_progress_reports_paths(session_with_frames):
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.api.state import active_session

    tmp = session_with_frames
    client = TestClient(app)
    started = client.post("/api/export", json={
        "session_id": active_session().session_id,
        "destination": str(tmp / "exports"),
        "name": "ds",
        "formats": ["yolo"],
        "use_split": False,
        "zip": True,
    })
    assert started.status_code == 200, started.text

    progress = client.get(f"/api/export/{started.json()['export_id']}/progress").json()

    assert progress["status"] == "done", progress
    assert progress["zip_path"] == str(tmp / "exports" / "ds.zip")
    assert progress["output_path"] == str(tmp / "exports" / "ds")
    assert Path(progress["zip_path"]).is_file()


@pytest.mark.parametrize("use_split,expected", [
    (False, ["ds/_annotations.coco.json"]),
    (True, ["ds/test/_annotations.coco.json", "ds/train/_annotations.coco.json", "ds/val/_annotations.coco.json"]),
])
def test_api_coco_export_uses_underscore_file_name(session_with_frames, use_split, expected):
    tmp = session_with_frames
    job = _export(tmp, "ds", ["coco"], use_split=use_split)
    assert job.status == "done", job.current_file
    with zipfile.ZipFile(job.zip_path) as archive:
        jsons = sorted(n for n in archive.namelist() if n.endswith(".json"))
    # Com 3 imagens o split pode deixar val/test vazios; só confere os que existem.
    assert jsons and set(jsons) <= set(expected)
    assert not any(n.endswith("/annotations.json") for n in jsons)
