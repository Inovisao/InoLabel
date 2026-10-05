"""Labels de imagens com o mesmo nome em subpastas diferentes não podem se misturar.

Regressão: o .txt era nomeado só pelo stem da imagem. lote_a/img_000.jpg e
lote_b/img_000.jpg gravavam no mesmo labels/img_000.txt; o segundo sobrescrevia o
primeiro, e a exportação atribuía a caixa de uma imagem à outra.
"""

import asyncio
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.api import state
from app.api.routes import annotations as ann_routes
from app.api.routes import frames as frame_routes
from app.api.schemas import AnnotationUpsert
from app.core.label_paths import ambiguous_stems, label_path, legacy_label_path

W, H = 160, 120


def _dataset(root: Path, layout) -> list:
    paths = []
    for rel in layout:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(path), np.zeros((H, W, 3), dtype=np.uint8))
        paths.append(path)
    return sorted(paths)


@pytest.fixture()
def project():
    tmp = Path(tempfile.mkdtemp())
    state.reset_state()
    ann_routes.reset_annotations()
    frame_routes._loaded_from_disk.clear()
    yield tmp
    state.reset_state()
    ann_routes.reset_annotations()
    shutil.rmtree(tmp, ignore_errors=True)


def _start(tmp: Path, layout, mode="detection"):
    data = tmp / "dataset"
    frames = _dataset(data, layout)
    session = state.create_session(mode=mode, data_path=data, output_path=tmp / "projeto", classes=["carro", "moto"])
    state.frame_paths[:] = frames
    for i in range(len(frames)):
        state.frame_dims[i] = (W, H)
    return session


def _reopen():
    """Simula fechar e reabrir o projeto: a memória some, o disco fica."""
    state.annotation_store.clear()
    frame_routes._loaded_from_disk.clear()


def _load(index: int):
    frame_routes._lazy_load_from_disk(index, state.frame_paths[index], W, H)
    return state.annotation_store.get(index, [])


NESTED = ["lote_a/img_000.jpg", "lote_a/img_001.jpg", "lote_b/img_000.jpg", "lote_b/img_001.jpg"]


# ── caminho do label ─────────────────────────────────────────────────────────

def test_label_path_keeps_the_subfolder(tmp_path):
    data, out = tmp_path / "ds", tmp_path / "out"
    assert label_path(out, data / "lote_a" / "img.jpg", data) == out / "labels" / "lote_a" / "img.txt"
    assert label_path(out, data / "img.jpg", data) == out / "labels" / "img.txt"


def test_label_path_for_single_file_or_outside_dataset_uses_the_name(tmp_path):
    out = tmp_path / "out"
    single = tmp_path / "foto.jpg"
    assert label_path(out, single, single) == out / "labels" / "foto.txt"
    assert label_path(out, tmp_path / "fora" / "x.jpg", tmp_path / "ds") == out / "labels" / "x.txt"


def test_ambiguous_stems_lists_only_repeated_names(tmp_path):
    frames = [tmp_path / p for p in ("a/img.jpg", "b/img.png", "a/unica.jpg")]
    assert ambiguous_stems(frames) == {"img"}


# ── o cenário do bug ─────────────────────────────────────────────────────────

def test_same_name_in_two_folders_keeps_separate_labels(project):
    _start(project, NESTED)
    ann_routes.add_annotation(0, AnnotationUpsert(category_id=0, bbox=[10, 10, 60, 40]))   # lote_a/img_000
    ann_routes.add_annotation(2, AnnotationUpsert(category_id=1, bbox=[90, 60, 40, 40]))   # lote_b/img_000

    labels = project / "projeto" / "labels"
    assert sorted(p.relative_to(labels).as_posix() for p in labels.rglob("*.txt")) == [
        "lote_a/img_000.txt", "lote_b/img_000.txt",
    ]

    _reopen()
    first, second = _load(0), _load(2)
    assert [a.category_id for a in first] == [0]
    assert [a.category_id for a in second] == [1]
    assert first[0].bbox[0] == pytest.approx(10, abs=0.01)
    assert second[0].bbox[0] == pytest.approx(90, abs=0.01)


def test_unannotated_image_does_not_inherit_a_label_from_its_namesake(project):
    _start(project, NESTED)
    ann_routes.add_annotation(1, AnnotationUpsert(category_id=0, bbox=[20, 30, 50, 50]))   # lote_a/img_001

    _reopen()

    assert _load(3) == []          # lote_b/img_001 nunca foi anotada
    assert len(_load(1)) == 1


def test_export_has_exactly_the_annotated_images(project):
    from app.api.routes.export import _run_export
    from app.core.exporter import ExportJob

    _start(project, NESTED)
    for idx in (0, 1, 2):
        ann_routes.add_annotation(idx, AnnotationUpsert(category_id=0, bbox=[10, 10, 40, 40]))
    _reopen()   # a exportação relê do disco o que não está em memória

    job = state.create_export(ExportJob(
        destination=project / "exports", name="ds", formats=["yolo"], use_split=False,
    ))
    asyncio.run(_run_export(job.export_id))

    assert job.status == "done", job.current_file
    exported = sorted((project / "exports" / "ds" / "images" / "all").iterdir())
    assert len(exported) == 3


# ── projetos gravados antes da correção ──────────────────────────────────────

def test_legacy_flat_label_still_loads_when_the_name_is_unique(project):
    session = _start(project, ["lote_a/img_000.jpg", "lote_b/outra.jpg"])
    legacy = legacy_label_path(session.output_path, state.frame_paths[0])
    legacy.parent.mkdir(parents=True)
    legacy.write_text("1 0.5 0.5 0.25 0.25\n", encoding="utf-8")

    loaded = _load(0)

    assert [a.category_id for a in loaded] == [1]


def test_legacy_flat_label_is_not_guessed_for_repeated_names(project):
    """Com nomes repetidos não dá para saber de qual imagem era o label antigo."""
    session = _start(project, NESTED)
    legacy = legacy_label_path(session.output_path, state.frame_paths[0])
    legacy.parent.mkdir(parents=True)
    legacy.write_text("0 0.5 0.5 0.25 0.25\n", encoding="utf-8")

    assert _load(0) == []
    assert _load(2) == []
    assert legacy.exists()   # o arquivo antigo não é apagado


def test_saving_moves_a_unique_legacy_label_to_the_new_place(project):
    session = _start(project, ["lote_a/img_000.jpg", "lote_b/outra.jpg"])
    legacy = legacy_label_path(session.output_path, state.frame_paths[0])
    legacy.parent.mkdir(parents=True)
    legacy.write_text("1 0.5 0.5 0.25 0.25\n", encoding="utf-8")

    # Sem exibir o frame antes: a anotação salva não pode ser perdida.
    state.frame_dims.clear()
    ann_routes.add_annotation(0, AnnotationUpsert(category_id=0, bbox=[5, 5, 20, 20]))

    new = label_path(session.output_path, state.frame_paths[0], session.data_path)
    assert len(new.read_text(encoding="utf-8").splitlines()) == 2
    assert not legacy.exists()   # sem cópia velha para contar em dobro ou divergir


def test_flat_dataset_keeps_the_same_file_names_as_before(project):
    session = _start(project, ["img_000.jpg", "img_001.jpg"])
    ann_routes.add_annotation(1, AnnotationUpsert(category_id=0, bbox=[5, 5, 20, 20]))
    assert (session.output_path / "labels" / "img_001.txt").is_file()


# ── contagem de frames anotados ──────────────────────────────────────────────

def test_project_listing_counts_labels_in_subfolders(project):
    import json

    from app.api.routes.session import list_projects

    session = _start(project, NESTED)
    (session.output_path).mkdir(parents=True, exist_ok=True)
    (session.output_path / ".inolabel.json").write_text(
        json.dumps({"mode": "detection", "classes": ["carro"], "data_path": str(session.data_path)}),
        encoding="utf-8",
    )
    for idx in (0, 2, 3):
        ann_routes.add_annotation(idx, AnnotationUpsert(category_id=0, bbox=[5, 5, 20, 20]))

    entries = list_projects(str(session.output_path))

    assert entries[0].annotated_frames == 3


def test_annotating_an_unvisited_frame_keeps_what_was_already_saved(project):
    session = _start(project, NESTED)
    ann_routes.add_annotation(2, AnnotationUpsert(category_id=1, bbox=[10, 10, 30, 30]))
    _reopen()
    state.frame_dims.clear()   # frame ainda não exibido nesta sessão

    ann_routes.add_annotation(2, AnnotationUpsert(category_id=0, bbox=[60, 60, 20, 20]))

    saved = label_path(session.output_path, state.frame_paths[2], session.data_path)
    assert [line.split()[0] for line in saved.read_text(encoding="utf-8").splitlines()] == ["1", "0"]
