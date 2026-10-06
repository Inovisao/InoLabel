"""Pacote zipado de um dataset exportado: confere as referências e compacta.

Um dataset só serve fora da máquina que o gerou se tudo dentro do pacote se
referenciar entre si: cada imagem YOLO com o seu label, cada ``file_name`` do COCO
com a imagem ao lado, e nenhum caminho absoluto da máquina de origem.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app.annotation.infrastructure.export.export_dir import EXPORT_MARKER
from app.config import IMAGE_EXTENSIONS
from app.core.exporter import COCO_EXPORT_FILE_NAME

_IMAGE_EXTS = {ext.lower() for ext in IMAGE_EXTENSIONS}
_MAX_REPORTED_PROBLEMS = 20


class BrokenDatasetLinksError(ValueError):
    """O dataset exportado tem referências que não fecham; o pacote não é gerado."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        shown = "; ".join(self.problems[:3])
        extra = f" (+{len(self.problems) - 3})" if len(self.problems) > 3 else ""
        super().__init__(f"Dataset com referências quebradas: {shown}{extra}")


def _is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _IMAGE_EXTS


def _check_yolo(root: Path, problems: List[str]) -> Dict[str, int]:
    """Cada imagem em images/<split>/ tem um .txt em labels/<split>/ e vice-versa."""
    images_root, labels_root = root / "images", root / "labels"
    if not labels_root.is_dir():
        return {"yolo_images": 0, "yolo_labels": 0}
    if not (root / "data.yaml").is_file():
        problems.append("YOLO: data.yaml ausente")

    image_keys = {
        p.relative_to(images_root).with_suffix("").as_posix()
        for p in images_root.rglob("*") if _is_image(p)
    } if images_root.is_dir() else set()
    label_keys = {
        p.relative_to(labels_root).with_suffix("").as_posix()
        for p in labels_root.rglob("*.txt")
    }
    for key in sorted(image_keys - label_keys):
        problems.append(f"YOLO: imagem sem label: images/{key}")
    for key in sorted(label_keys - image_keys):
        problems.append(f"YOLO: label sem imagem: labels/{key}.txt")
    return {"yolo_images": len(image_keys), "yolo_labels": len(label_keys)}


def _check_coco(root: Path, problems: List[str]) -> Dict[str, int]:
    """Cada JSON COCO referencia imagens que existem na pasta images/ ao lado.

    Aceita o nome atual (_annotations.coco.json) e o de exportações anteriores
    (annotations*.json).
    """
    files = images = annotations = 0
    coco_files = {*root.rglob(COCO_EXPORT_FILE_NAME), *root.rglob("annotations*.json")}
    for json_path in sorted(coco_files):
        rel = json_path.relative_to(root).as_posix()
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            problems.append(f"COCO: {rel} ilegível")
            continue
        if not isinstance(data, dict):
            problems.append(f"COCO: {rel} não é um objeto COCO")
            continue
        files += 1
        image_ids = set()
        for img in data.get("images", []):
            images += 1
            image_ids.add(img.get("id"))
            name = str(img.get("file_name", ""))
            # Imagens em images/ (layout InoLabel) ou ao lado do JSON (layout Roboflow).
            found = name and any((folder / name).is_file() for folder in (json_path.parent / "images", json_path.parent))
            if not found:
                problems.append(f"COCO: {rel} aponta para imagem ausente: {name or '(sem nome)'}")
        category_ids = {cat.get("id") for cat in data.get("categories", [])}
        for ann in data.get("annotations", []):
            annotations += 1
            if ann.get("image_id") not in image_ids:
                problems.append(f"COCO: {rel} anotação {ann.get('id')} sem imagem correspondente")
            if ann.get("category_id") not in category_ids:
                problems.append(f"COCO: {rel} anotação {ann.get('id')} com categoria inexistente")
    return {"coco_files": files, "coco_images": images, "coco_annotations": annotations}


def verify_dataset_links(root: Path) -> Dict[str, int]:
    """Confere as referências internas do dataset; BrokenDatasetLinksError se algo não fecha."""
    root = Path(root)
    if not root.is_dir():
        raise BrokenDatasetLinksError([f"pasta do dataset não encontrada: {root.name}"])
    problems: List[str] = []
    report = {**_check_yolo(root, problems), **_check_coco(root, problems)}
    if not report.get("yolo_labels") and not report.get("coco_files"):
        problems.append("nenhum dataset YOLO ou COCO encontrado na pasta")
    if problems:
        raise BrokenDatasetLinksError(problems[:_MAX_REPORTED_PROBLEMS])
    return report


def portable_data_yaml(text: str) -> str:
    """Remove a linha ``path:`` (absoluta na máquina de origem) do data.yaml.

    Sem ``path``, o Ultralytics usa a pasta do próprio data.yaml como raiz do
    dataset, e os caminhos relativos ``images/...`` valem em qualquer máquina.
    """
    return "".join(
        line for line in text.splitlines(keepends=True) if not line.lstrip().startswith("path:")
    )


def zip_dataset(
    root: Path,
    zip_path: Optional[Path] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Path:
    """Compacta a pasta do dataset em ``<root>.zip`` com uma única pasta-raiz dentro.

    Escrita atômica: o zip é montado em ``.tmp`` e só então substitui o anterior.
    Imagens entram sem recompressão (já são comprimidas); texto entra com deflate.
    """
    root = Path(root)
    zip_path = Path(zip_path) if zip_path is not None else root.with_name(root.name + ".zip")
    files = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.name != EXPORT_MARKER and p.suffix != ".tmp"
    )
    tmp_path = zip_path.with_name(zip_path.name + ".tmp")
    total = len(files)
    try:
        with zipfile.ZipFile(tmp_path, "w") as archive:
            for done, path in enumerate(files, 1):
                arcname = (Path(root.name) / path.relative_to(root)).as_posix()
                if path.name == "data.yaml":
                    archive.writestr(
                        arcname, portable_data_yaml(path.read_text(encoding="utf-8")),
                        compress_type=zipfile.ZIP_DEFLATED,
                    )
                else:
                    compression = zipfile.ZIP_STORED if _is_image(path) else zipfile.ZIP_DEFLATED
                    archive.write(path, arcname, compress_type=compression)
                if on_progress:
                    on_progress(done, total, path.name)
        tmp_path.replace(zip_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return zip_path
