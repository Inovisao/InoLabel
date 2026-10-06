#!/usr/bin/env python3
"""Confere se as anotações de um dataset exportado estão corretas.

Aceita a raiz de uma exportação ou uma pasta de split (ex.: ``dataset_export/train``),
em COCO ou YOLO. A saída é só agregada (contagens e tipos de problema); exemplos
aparecem como código anônimo (``<arquivo 3f2a91c0>``), nunca pelo nome (LGPD).

Uso:
    python utils/verificar_export.py "<pasta exportada>"

Código de saída: 0 sem problemas, 1 com problemas, 2 se a pasta não for um dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Rodado como script (python utils/x.py), a raiz do projeto nao esta no sys.path.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import IMAGE_EXTENSIONS  # noqa: E402
from app.log_privacy import log_ref  # noqa: E402

IMAGE_EXTS = {ext.lower() for ext in IMAGE_EXTENSIONS}
COCO_NAMES = ("_annotations.coco.json", "annotations.coco.json", "annotations.json")
TOLERANCE_PX = 0.5      # folga para arredondamento de coordenadas
MAX_EXAMPLES = 5


class Report:
    def __init__(self) -> None:
        self.counts: Counter = Counter()
        self.problems: Dict[str, List[str]] = defaultdict(list)

    def problem(self, kind: str, ref: object = None) -> None:
        refs = self.problems[kind]
        refs.append(log_ref(ref) if ref is not None else "")

    @property
    def ok(self) -> bool:
        return not self.problems


def _image_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        from PIL import Image

        with Image.open(path) as im:
            return im.size  # (largura, altura)
    except Exception:
        return None


def _find_image(base: Path, file_name: str) -> Optional[Path]:
    """COCO do InoLabel guarda as imagens em images/ ao lado; o padrão Roboflow, na mesma pasta."""
    for folder in (base / "images", base):
        candidate = folder / file_name
        if candidate.is_file():
            return candidate
    return None


# ── COCO ─────────────────────────────────────────────────────────────────────

def check_coco(json_path: Path, report: Report) -> None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report.problem("COCO: JSON ilegível", json_path.name)
        return
    if not isinstance(data, dict):
        report.problem("COCO: o arquivo não é um objeto COCO", json_path.name)
        return
    for key in ("images", "annotations", "categories"):
        if not isinstance(data.get(key), list):
            report.problem(f"COCO: chave '{key}' ausente ou não é lista")
    images = data.get("images") or []
    annotations = data.get("annotations") or []
    categories = data.get("categories") or []
    report.counts["coco_arquivos"] += 1
    report.counts["coco_imagens"] += len(images)
    report.counts["coco_anotacoes"] += len(annotations)
    report.counts["coco_categorias"] = max(report.counts["coco_categorias"], len(categories))

    category_ids = {c.get("id") for c in categories}
    if len(category_ids) != len(categories):
        report.problem("COCO: id de categoria repetido")

    by_id: Dict[object, dict] = {}
    real_size: Dict[object, Tuple[int, int]] = {}
    for img in images:
        image_id, name = img.get("id"), str(img.get("file_name", ""))
        if image_id in by_id:
            report.problem("COCO: id de imagem repetido", name)
        by_id[image_id] = img
        path = _find_image(json_path.parent, name) if name else None
        if path is None:
            report.problem("COCO: imagem do JSON não existe na pasta", name or None)
            continue
        size = _image_size(path)
        if size is None:
            report.problem("COCO: imagem ilegível", name)
            continue
        real_size[image_id] = size
        if (int(img.get("width", 0) or 0), int(img.get("height", 0) or 0)) != size:
            report.problem("COCO: width/height do JSON diferente da imagem real", name)

    seen_ann_ids = set()
    boxes_per_image: Dict[object, Counter] = defaultdict(Counter)
    for ann in annotations:
        ann_id, image_id = ann.get("id"), ann.get("image_id")
        name = (by_id.get(image_id) or {}).get("file_name")
        if ann_id in seen_ann_ids:
            report.problem("COCO: id de anotação repetido", name)
        seen_ann_ids.add(ann_id)
        if image_id not in by_id:
            report.problem("COCO: anotação aponta para imagem inexistente")
            continue
        if ann.get("category_id") not in category_ids:
            report.problem("COCO: anotação com categoria inexistente", name)
        bbox = ann.get("bbox")
        try:
            x, y, w, h = (float(v) for v in bbox)
        except (TypeError, ValueError):
            report.problem("COCO: bbox inválida (não são 4 números)", name)
            continue
        if w <= 0 or h <= 0:
            report.problem("COCO: bbox sem área (largura ou altura <= 0)", name)
        size = real_size.get(image_id)
        if size is not None:
            width, height = size
            if x < -TOLERANCE_PX or y < -TOLERANCE_PX or x + w > width + TOLERANCE_PX or y + h > height + TOLERANCE_PX:
                report.problem("COCO: bbox sai da imagem", name)
        area = ann.get("area")
        if isinstance(area, (int, float)) and w > 0 and h > 0 and abs(area - w * h) > max(1.0, 0.01 * w * h):
            report.problem("COCO: area diferente de largura x altura", name)
        key = (ann.get("category_id"), round(x, 1), round(y, 1), round(w, 1), round(h, 1))
        boxes_per_image[image_id][key] += 1
        report.counts["coco_anotacoes_por_classe:" + str(ann.get("category_id"))] += 1

    for image_id, boxes in boxes_per_image.items():
        if any(n > 1 for n in boxes.values()):
            report.problem("COCO: caixa duplicada (mesma classe e posição) na mesma imagem",
                           by_id[image_id].get("file_name"))
    report.counts["coco_imagens_sem_anotacao"] += sum(1 for i in by_id if i not in boxes_per_image)


# ── YOLO ─────────────────────────────────────────────────────────────────────

def _yolo_class_count(root: Path) -> Optional[int]:
    for candidate in (root / "data.yaml", root.parent / "data.yaml", root.parent.parent / "data.yaml"):
        if candidate.is_file():
            names = [line for line in candidate.read_text(encoding="utf-8").splitlines()
                     if line.startswith("  ") and ":" in line]
            return len(names) or None
    return None


def check_yolo(images_dir: Path, labels_dir: Path, report: Report, n_classes: Optional[int]) -> None:
    images = {p.relative_to(images_dir).with_suffix("").as_posix(): p
              for p in images_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS}
    labels = {p.relative_to(labels_dir).with_suffix("").as_posix(): p for p in labels_dir.rglob("*.txt")}
    report.counts["yolo_imagens"] += len(images)
    report.counts["yolo_labels"] += len(labels)
    for key in images.keys() - labels.keys():
        report.problem("YOLO: imagem sem arquivo de label", key)
    for key in labels.keys() - images.keys():
        report.problem("YOLO: label sem imagem", key)

    for key, label_path in labels.items():
        lines = [line.split() for line in label_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            report.counts["yolo_labels_vazios"] += 1
        seen = Counter()
        for parts in lines:
            report.counts["yolo_caixas"] += 1
            if len(parts) not in (5, 9):
                report.problem("YOLO: linha com quantidade de valores inválida", key)
                continue
            try:
                cls = int(parts[0])
                values = [float(v) for v in parts[1:]]
            except ValueError:
                report.problem("YOLO: valor não numérico", key)
                continue
            report.counts[f"yolo_caixas_por_classe:{cls}"] += 1
            if cls < 0 or (n_classes is not None and cls >= n_classes):
                report.problem("YOLO: classe fora do data.yaml", key)
            if any(v < 0.0 or v > 1.0 for v in values):
                report.problem("YOLO: coordenada fora de [0, 1]", key)
            if len(parts) == 5:
                cx, cy, w, h = values
                if w <= 0 or h <= 0:
                    report.problem("YOLO: caixa sem área", key)
                eps = TOLERANCE_PX / 1000
                if cx - w / 2 < -eps or cy - h / 2 < -eps or cx + w / 2 > 1 + eps or cy + h / 2 > 1 + eps:
                    report.problem("YOLO: caixa sai da imagem", key)
            seen[tuple(parts)] += 1
        if any(n > 1 for n in seen.values()):
            report.problem("YOLO: caixa duplicada no mesmo label", key)


# ── detecção do formato ──────────────────────────────────────────────────────

def verify(root: Path) -> Optional[Report]:
    root = Path(root)
    report = Report()
    found = False
    coco_files = sorted({p for name in COCO_NAMES for p in root.rglob(name)})
    for json_path in coco_files:
        found = True
        check_coco(json_path, report)
    # YOLO: raiz (images/<split>, labels/<split>) ou pasta já no nível images/labels
    if (root / "images").is_dir() and (root / "labels").is_dir():
        found = True
        check_yolo(root / "images", root / "labels", report, _yolo_class_count(root))
    elif root.parent.name in ("images", "labels") or (root.parent / "labels").is_dir():
        split = root.name
        base = root.parent.parent if root.parent.name in ("images", "labels") else root.parent
        if (base / "images" / split).is_dir() and (base / "labels" / split).is_dir():
            found = True
            check_yolo(base / "images" / split, base / "labels" / split, report, _yolo_class_count(base))
    return report if found else None


def print_report(report: Report) -> None:
    print("== Contagens")
    for key in sorted(k for k in report.counts if ":" not in k):
        print(f"   {key}: {report.counts[key]}")
    per_class = sorted(k for k in report.counts if ":" in k)
    if per_class:
        print("== Por classe (id: quantidade)")
        for key in per_class:
            print(f"   {key.split(':', 1)[0]} {key.split(':', 1)[1]}: {report.counts[key]}")
    if report.ok:
        print("== Nenhum problema encontrado.")
        return
    print("== Problemas")
    for kind, refs in sorted(report.problems.items()):
        examples = ", ".join(r for r in refs[:MAX_EXAMPLES] if r)
        print(f"   [{len(refs)}] {kind}" + (f"  ex.: {examples}" if examples else ""))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pasta", type=Path, help="Pasta exportada (raiz ou split)")
    args = parser.parse_args(argv)
    if not args.pasta.is_dir():
        print("A pasta informada não existe.")
        return 2
    report = verify(args.pasta)
    if report is None:
        print("Nenhum dataset COCO ou YOLO encontrado nesta pasta.")
        return 2
    print_report(report)
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
