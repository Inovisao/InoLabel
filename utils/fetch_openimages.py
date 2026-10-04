#!/usr/bin/env python3
"""Baixa do Open Images candidatas a selfie com acessorio, separadas por classe, para revisao manual.

Nada entra no dataset automaticamente: as imagens vao para <output>/<classe>/, voce revisa,
apaga as ruins e move as aprovadas para o dataset. Cada pasta tem um candidates.csv com a
licenca, o autor e as caixas do Open Images (coordenadas normalizadas) de cada imagem.

Filtro de "selfie": exatamente um rosto (Human face) sem IsGroupOf, rosto ocupando ao menos
--min-face-area da imagem, e ao menos uma caixa da classe alvo encostando no rosto.

Imagens com licenca CC BY 2.0: ao usar, mantenha a atribuicao (autor + link) do candidates.csv.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

BBOX_URLS = {
    "validation": "https://storage.googleapis.com/openimages/v5/validation-annotations-bbox.csv",
    "test": "https://storage.googleapis.com/openimages/v5/test-annotations-bbox.csv",
    "train": "https://storage.googleapis.com/openimages/v6/oidv6-train-annotations-bbox.csv",
}
METADATA_URLS = {
    "validation": "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv",
    "test": "https://storage.googleapis.com/openimages/2018_04/test/test-images-with-rotation.csv",
    "train": "https://storage.googleapis.com/openimages/2018_04/train/train-images-boxable-with-rotation.csv",
}
IMAGE_URL = "https://open-images-dataset.s3.amazonaws.com/{split}/{image_id}.jpg"

HUMAN_FACE = "/m/0dzct"
# Dataset class -> Open Images labels. Open Images has no face-mask class.
CLASS_LABELS: Dict[str, Dict[str, str]] = {
    "hat": {
        "/m/02dl1y": "Hat",
        "/m/02wbtzl": "Sun hat",
        "/m/025rp__": "Cowboy hat",
        "/m/02fq_6": "Fedora",
        "/m/02jfl0": "Sombrero",
    },
    "glasses": {
        "/m/0jyfg": "Glasses",
        "/m/017ftj": "Sunglasses",
    },
}


@dataclass
class Box:
    label: str
    x1: float
    x2: float
    y1: float
    y2: float
    is_group: bool = False
    is_depiction: bool = False

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


@dataclass
class Candidate:
    image_id: str
    split: str
    target_boxes: List[Box]
    face: Box
    metadata: Dict[str, str] = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa candidatas do Open Images por classe para revisao manual (nao altera o dataset)."
    )
    parser.add_argument("--classes", nargs="+", default=["hat"], choices=sorted(CLASS_LABELS))
    parser.add_argument("--output", type=Path, default=Path("openimages_candidates"))
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["validation", "test"],
        choices=list(BBOX_URLS),
        help="'train' tem muito mais imagens, mas le um CSV de 2,2 GB em streaming (varios minutos).",
    )
    parser.add_argument("--limit", type=int, default=150, help="Maximo de imagens baixadas por classe.")
    parser.add_argument(
        "--min-face-area",
        type=float,
        default=0.06,
        help="Fracao minima da imagem ocupada pelo rosto (0.06 = 6%%). Maior = mais cara de selfie.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def stream_filtered_rows(url: str, cache_path: Path, keep, label: str) -> List[Dict[str, str]]:
    """Streams a remote CSV keeping only rows accepted by `keep`; caches the kept rows."""
    if cache_path.exists():
        with cache_path.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    kept: List[Dict[str, str]] = []
    fieldnames: Optional[Sequence[str]] = None
    with urllib.request.urlopen(url, timeout=60) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8", newline=""))
        fieldnames = reader.fieldnames
        for count, row in enumerate(reader, 1):
            if keep(row):
                kept.append(row)
            if count % 1_000_000 == 0:
                print(f"[INFO] {label}: {count:,} linhas lidas, {len(kept):,} mantidas", flush=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames or []))
        writer.writeheader()
        writer.writerows(kept)
    tmp.replace(cache_path)
    return kept


def _row_to_box(row: Dict[str, str]) -> Box:
    return Box(
        label=row["LabelName"],
        x1=float(row["XMin"]),
        x2=float(row["XMax"]),
        y1=float(row["YMin"]),
        y2=float(row["YMax"]),
        is_group=row.get("IsGroupOf") == "1",
        is_depiction=row.get("IsDepiction") == "1",
    )


def _touches_face(box: Box, face: Box, margin: float = 0.5) -> bool:
    """True if `box` intersects the face box grown by `margin` of its size (hats sit above it)."""
    w, h = face.x2 - face.x1, face.y2 - face.y1
    fx1, fx2 = face.x1 - w * margin, face.x2 + w * margin
    fy1, fy2 = face.y1 - h * margin, face.y2 + h * margin
    return box.x1 < fx2 and box.x2 > fx1 and box.y1 < fy2 and box.y2 > fy1


def select_candidates(
    rows: Iterable[Dict[str, str]],
    split: str,
    target_labels: Set[str],
    min_face_area: float,
) -> List[Candidate]:
    """Picks selfie-like images: one real face, large enough, with a target box on it."""
    by_image: Dict[str, List[Box]] = {}
    for row in rows:
        by_image.setdefault(row["ImageID"], []).append(_row_to_box(row))

    candidates: List[Candidate] = []
    for image_id, boxes in by_image.items():
        faces = [b for b in boxes if b.label == HUMAN_FACE]
        if len(faces) != 1:
            continue
        face = faces[0]
        if face.is_group or face.is_depiction or face.area < min_face_area:
            continue
        targets = [
            b for b in boxes
            if b.label in target_labels and not b.is_group and not b.is_depiction and _touches_face(b, face)
        ]
        if targets:
            candidates.append(Candidate(image_id=image_id, split=split, target_boxes=targets, face=face))
    return candidates


def _download(candidate: Candidate, dest: Path) -> bool:
    if dest.exists():
        return True
    url = IMAGE_URL.format(split=candidate.split, image_id=candidate.image_id)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[AVISO] Falha ao baixar {candidate.image_id}: {exc}")
        return False
    tmp = dest.with_suffix(".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return True


def _write_manifest(path: Path, class_name: str, candidates: List[Candidate]):
    labels = CLASS_LABELS[class_name]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "file", "image_id", "split", "openimages_labels", "boxes_xyxy_normalized",
            "license", "author", "author_profile", "landing_url",
        ])
        for c in candidates:
            meta = c.metadata
            writer.writerow([
                f"{c.image_id}.jpg",
                c.image_id,
                c.split,
                ";".join(sorted({labels[b.label] for b in c.target_boxes})),
                ";".join(f"{b.x1:.4f},{b.y1:.4f},{b.x2:.4f},{b.y2:.4f}" for b in c.target_boxes),
                meta.get("License", ""),
                meta.get("Author", ""),
                meta.get("AuthorProfileURL", ""),
                meta.get("OriginalLandingURL", ""),
            ])


def main() -> int:
    args = parse_args()
    output: Path = args.output
    cache_dir = output / ".cache"
    wanted_labels = {HUMAN_FACE}
    for class_name in args.classes:
        wanted_labels.update(CLASS_LABELS[class_name])

    per_class: Dict[str, List[Candidate]] = {name: [] for name in args.classes}
    for split in args.splits:
        print(f"[INFO] Lendo caixas do split {split}...")
        rows = stream_filtered_rows(
            BBOX_URLS[split],
            cache_dir / f"{split}-bbox-{'-'.join(sorted(args.classes))}.csv",
            lambda row: row["LabelName"] in wanted_labels,
            f"bbox {split}",
        )
        for class_name in args.classes:
            found = select_candidates(rows, split, set(CLASS_LABELS[class_name]), args.min_face_area)
            print(f"[INFO] {split}: {len(found)} candidatas para '{class_name}'")
            per_class[class_name].extend(found)

    rng = random.Random(args.seed)
    chosen: Dict[str, List[Candidate]] = {}
    for class_name, found in per_class.items():
        found.sort(key=lambda c: c.image_id)
        rng.shuffle(found)
        chosen[class_name] = found[: args.limit]

    # License/author metadata, only for the chosen images.
    for split in args.splits:
        ids = {c.image_id for items in chosen.values() for c in items if c.split == split}
        if not ids:
            continue
        print(f"[INFO] Lendo licencas do split {split}...")
        ids_key = hashlib.md5(",".join(sorted(ids)).encode("utf-8")).hexdigest()[:10]
        meta_rows = stream_filtered_rows(
            METADATA_URLS[split],
            cache_dir / f"{split}-metadata-{ids_key}.csv",
            lambda row, ids=ids: row["ImageID"] in ids,
            f"metadata {split}",
        )
        meta_by_id = {row["ImageID"]: row for row in meta_rows}
        for items in chosen.values():
            for c in items:
                if c.split == split:
                    c.metadata = meta_by_id.get(c.image_id, {})

    for class_name, items in chosen.items():
        class_dir = output / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Baixando {len(items)} imagens de '{class_name}' em {class_dir}...")
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            ok = list(pool.map(lambda c: _download(c, class_dir / f"{c.image_id}.jpg"), items))
        downloaded = [c for c, success in zip(items, ok) if success]
        _write_manifest(class_dir / "candidates.csv", class_name, downloaded)
        print(f"[OK] {class_name}: {len(downloaded)} imagens em {class_dir}")

    print("Revise as pastas, apague o que nao servir e mova as aprovadas para o dataset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
