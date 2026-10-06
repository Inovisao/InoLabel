"""utils/verificar_export.py: confere anotações exportadas sem expor nomes de arquivo."""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from utils.verificar_export import main, verify

W, H = 40, 30


def _img(path: Path, w=W, h=H):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), np.zeros((h, w, 3), dtype=np.uint8))


def _coco(split: Path, annotations, images=None):
    _img(split / "images" / "joao_silva_01.jpg")
    payload = {
        "images": images or [{"id": 1, "file_name": "joao_silva_01.jpg", "width": W, "height": H}],
        "annotations": annotations,
        "categories": [{"id": 0, "name": "fruto"}],
    }
    (split / "_annotations.coco.json").write_text(json.dumps(payload), encoding="utf-8")
    return split


def _ann(i, bbox, cat=0):
    return {"id": i, "image_id": 1, "category_id": cat, "bbox": bbox, "area": bbox[2] * bbox[3]}


def kinds(report):
    return set(report.problems)


def test_correct_coco_split_has_no_problems(tmp_path):
    report = verify(_coco(tmp_path / "train", [_ann(1, [2, 2, 10, 10])]))
    assert report.ok
    assert report.counts["coco_anotacoes"] == 1


@pytest.mark.parametrize("annotations,images,expected", [
    ([_ann(1, [35, 2, 10, 10])], None, "COCO: bbox sai da imagem"),
    ([_ann(1, [2, 2, 0, 10])], None, "COCO: bbox sem área (largura ou altura <= 0)"),
    ([_ann(1, [2, 2, 10, 10], cat=5)], None, "COCO: anotação com categoria inexistente"),
    ([_ann(1, [2, 2, 10, 10]), _ann(2, [2, 2, 10, 10])], None,
     "COCO: caixa duplicada (mesma classe e posição) na mesma imagem"),
    ([_ann(1, [2, 2, 10, 10]), _ann(1, [5, 5, 5, 5])], None, "COCO: id de anotação repetido"),
    ([_ann(1, [2, 2, 10, 10])], [{"id": 1, "file_name": "joao_silva_01.jpg", "width": 99, "height": H}],
     "COCO: width/height do JSON diferente da imagem real"),
    ([_ann(1, [2, 2, 10, 10])], [{"id": 1, "file_name": "nao_existe.jpg", "width": W, "height": H}],
     "COCO: imagem do JSON não existe na pasta"),
])
def test_coco_problems_are_detected(tmp_path, annotations, images, expected):
    report = verify(_coco(tmp_path / "train", annotations, images))
    assert expected in kinds(report)


def test_wrong_area_is_detected(tmp_path):
    ann = _ann(1, [2, 2, 10, 10])
    ann["area"] = 7
    assert "COCO: area diferente de largura x altura" in kinds(verify(_coco(tmp_path / "train", [ann])))


def test_roboflow_layout_with_images_next_to_json(tmp_path):
    split = tmp_path / "train"
    _img(split / "a.jpg")
    (split / "_annotations.coco.json").write_text(json.dumps({
        "images": [{"id": 1, "file_name": "a.jpg", "width": W, "height": H}],
        "annotations": [_ann(1, [1, 1, 5, 5])], "categories": [{"id": 0, "name": "x"}],
    }), encoding="utf-8")
    assert verify(split).ok


def _yolo(root: Path, lines, split="train"):
    _img(root / "images" / split / "a.jpg")
    label = root / "labels" / split / "a.txt"
    label.parent.mkdir(parents=True, exist_ok=True)
    label.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "data.yaml").write_text("train: images/train\n\nnames:\n  0: fruto\n", encoding="utf-8")
    return root


def test_correct_yolo_root_and_split_dir(tmp_path):
    root = _yolo(tmp_path / "ds", ["0 0.5 0.5 0.2 0.2"])
    assert verify(root).ok
    assert verify(root / "images" / "train").ok


@pytest.mark.parametrize("line,expected", [
    ("3 0.5 0.5 0.2 0.2", "YOLO: classe fora do data.yaml"),
    ("0 1.2 0.5 0.2 0.2", "YOLO: coordenada fora de [0, 1]"),
    ("0 0.95 0.5 0.2 0.2", "YOLO: caixa sai da imagem"),
    ("0 0.5 0.5 0 0.2", "YOLO: caixa sem área"),
    ("0 0.5 0.5", "YOLO: linha com quantidade de valores inválida"),
])
def test_yolo_problems_are_detected(tmp_path, line, expected):
    assert expected in kinds(verify(_yolo(tmp_path / "ds", [line])))


def test_output_never_shows_file_names(tmp_path, capsys):
    split = _coco(tmp_path / "train", [_ann(1, [35, 2, 10, 10])])
    code = main([str(split)])
    out = capsys.readouterr().out
    assert code == 1
    assert "joao" not in out and "silva" not in out
    assert "<arquivo " in out


def test_not_a_dataset(tmp_path, capsys):
    (tmp_path / "vazia").mkdir()
    assert main([str(tmp_path / "vazia")]) == 2


@pytest.mark.parametrize("fmt,use_split", [("coco", True), ("coco", False), ("yolo", True), ("yolo", False)])
def test_exports_made_by_the_app_pass(fmt, use_split):
    """O verificador concorda com o que o próprio app exporta."""
    from app.api.routes.export import _run_export
    from app.api.schemas import Annotation
    from app.api.state import annotation_store, create_export, create_session, frame_dims, frame_paths, next_ann_id, reset_state
    from app.core.exporter import ExportJob

    tmp = Path(tempfile.mkdtemp())
    try:
        reset_state()
        create_session(mode="detection", data_path=tmp / "ds", output_path=tmp / "proj", classes=["fruto", "folha"])
        for i in range(6):
            path = tmp / "ds" / f"f{i}.jpg"
            _img(path, 64, 48)
            frame_paths.append(path)
            frame_dims[i] = (64, 48)
            annotation_store[i] = [Annotation(id=next_ann_id[0], image_id=i, category_id=i % 2, bbox=[50.0, 40.0, 30.0, 20.0])]
            next_ann_id[0] += 1
        job = create_export(ExportJob(destination=tmp / "exp", name="ds", formats=[fmt], use_split=use_split))
        asyncio.run(_run_export(job.export_id))
        assert job.status == "done", job.current_file
        report = verify(tmp / "exp" / "ds")
        assert report is not None and report.ok, dict(report.problems)
    finally:
        reset_state()
        shutil.rmtree(tmp, ignore_errors=True)


# ── keypoints (YOLO Pose e COCO Keypoints) ───────────────────────────────────

def _pose(root: Path, lines):
    _yolo(root, lines)
    (root / "data.yaml").write_text("train: images/train\n\nkpt_shape: [2, 3]\n\nnames:\n  0: fruto\n", encoding="utf-8")
    return root


def test_yolo_pose_lines_are_valid(tmp_path):
    # instância de um ponto só: caixa sem área, segundo ponto ausente
    root = _pose(tmp_path / "ds", ["0 0.5 0.5 0.0 0.0 0.5 0.5 2 0.0 0.0 0"])
    assert verify(root).ok


@pytest.mark.parametrize("line,expected", [
    ("0 0.5 0.5 0.2 0.2 0.5 0.5 3 0.1 0.1 2", "YOLO: visibilidade de keypoint fora de 0, 1 ou 2"),
    ("0 0.5 0.5 0.2 0.2 1.5 0.5 2 0.1 0.1 2", "YOLO: coordenada fora de [0, 1]"),
    ("0 0.5 0.5 0.2 0.2 0.5 0.5 2", "YOLO: linha com quantidade de valores inválida"),
])
def test_yolo_pose_problems_are_detected(tmp_path, line, expected):
    assert expected in kinds(verify(_pose(tmp_path / "ds", [line])))


def _kp_coco(split: Path, keypoints, num=None):
    ann = {"id": 1, "image_id": 1, "category_id": 0, "bbox": [10, 10, 0, 0], "area": 0, "keypoints": keypoints}
    if num is not None:
        ann["num_keypoints"] = num
    _coco(split, [ann])
    data = json.loads((split / "_annotations.coco.json").read_text(encoding="utf-8"))
    data["categories"][0]["keypoints"] = ["a", "b"]
    (split / "_annotations.coco.json").write_text(json.dumps(data), encoding="utf-8")
    return split


def test_coco_keypoint_single_point_is_valid(tmp_path):
    assert verify(_kp_coco(tmp_path / "train", [10, 10, 2, 0, 0, 0], num=1)).ok


@pytest.mark.parametrize("keypoints,num,expected", [
    ([10, 10, 2], None, "COCO: keypoints com quantidade diferente da declarada na categoria"),
    ([0, 0, 0, 0, 0, 0], None, "COCO: instância de keypoint sem nenhum ponto marcado"),
    ([10, 10, 2, 500, 10, 2], None, "COCO: keypoint fora da imagem"),
    ([10, 10, 2, 5, 5, 2], 1, "COCO: num_keypoints diferente dos pontos marcados"),
])
def test_coco_keypoint_problems_are_detected(tmp_path, keypoints, num, expected):
    assert expected in kinds(verify(_kp_coco(tmp_path / "train", keypoints, num)))
