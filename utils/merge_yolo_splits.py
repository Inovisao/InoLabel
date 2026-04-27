#!/usr/bin/env python3
"""Consolida um dataset YOLO com train/val/test em um unico split train."""

import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Junta images/labels de train, val e test em um unico split train."
    )
    parser.add_argument("input", type=Path, help="Diretorio raiz do dataset YOLO de entrada")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Diretorio do dataset consolidado. Padrao: <input>_train_only",
    )
    return parser.parse_args()


def _load_names_from_yaml(data_yaml_path: Path) -> Dict[int, str]:
    names: Dict[int, str] = {}
    in_names_block = False
    for raw_line in data_yaml_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "names:":
            in_names_block = True
            continue
        if not in_names_block:
            continue
        if ":" not in stripped:
            continue
        key_text, value_text = stripped.split(":", 1)
        key_text = key_text.strip()
        value_text = value_text.strip()
        if not key_text.isdigit():
            continue
        names[int(key_text)] = value_text
    return dict(sorted(names.items()))


def _format_train_only_yaml(dataset_root: Path, names: Dict[int, str]) -> str:
    lines = [
        f"path: {dataset_root.resolve()}",
        "train: images/train",
        "",
        "names:",
    ]
    for class_id, name in sorted(names.items()):
        lines.append(f"  {class_id}: {name}")
    return "\n".join(lines) + "\n"


def merge_yolo_splits(input_root: Path, output_root: Path) -> Dict[str, object]:
    data_yaml_path = input_root / "data.yaml"
    if not data_yaml_path.exists():
        raise FileNotFoundError(f"data.yaml nao encontrado em {input_root}")

    names = _load_names_from_yaml(data_yaml_path)
    if not names:
        raise ValueError(f"Nenhuma classe encontrada em {data_yaml_path}")

    if output_root.exists():
        shutil.rmtree(output_root)

    target_images_dir = output_root / "images" / "train"
    target_labels_dir = output_root / "labels" / "train"
    target_images_dir.mkdir(parents=True, exist_ok=True)
    target_labels_dir.mkdir(parents=True, exist_ok=True)

    merged_counts = {"train": 0, "val": 0, "test": 0}
    empty_label_files = 0
    copied_files: List[Tuple[str, str]] = []
    seen_image_names = set()
    seen_label_names = set()

    for split in ("train", "val", "test"):
        source_images_dir = input_root / "images" / split
        source_labels_dir = input_root / "labels" / split
        if not source_images_dir.exists():
            continue

        for image_path in sorted(path for path in source_images_dir.iterdir() if path.is_file()):
            label_path = source_labels_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                raise FileNotFoundError(f"Label ausente para imagem {image_path.name}: {label_path}")
            if image_path.name in seen_image_names:
                raise ValueError(f"Nome de imagem duplicado entre splits: {image_path.name}")
            if label_path.name in seen_label_names:
                raise ValueError(f"Nome de label duplicado entre splits: {label_path.name}")

            shutil.copy2(image_path, target_images_dir / image_path.name)
            shutil.copy2(label_path, target_labels_dir / label_path.name)

            seen_image_names.add(image_path.name)
            seen_label_names.add(label_path.name)
            merged_counts[split] += 1
            copied_files.append((split, image_path.name))
            if label_path.read_text(encoding="utf-8") == "":
                empty_label_files += 1

    output_yaml_path = output_root / "data.yaml"
    output_yaml_path.write_text(_format_train_only_yaml(output_root, names), encoding="utf-8")

    return {
        "output_root": output_root.resolve(),
        "data_yaml": output_yaml_path.resolve(),
        "merged_counts": merged_counts,
        "total_images": len(copied_files),
        "empty_label_files": empty_label_files,
        "names": names,
    }


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Dataset YOLO nao encontrado: {args.input}")

    output_root = args.output_root or args.input.with_name(f"{args.input.name}_train_only")
    report = merge_yolo_splits(args.input, output_root)

    print(f"[OK] Dataset consolidado em: {report['output_root']}")
    print(f"[OK] data.yaml: {report['data_yaml']}")
    print(f"[INFO] Imagens unificadas por split de origem: {report['merged_counts']}")
    print(f"[INFO] Total de imagens: {report['total_images']}")
    print(f"[INFO] Labels vazios preservados: {report['empty_label_files']}")
    print(f"[INFO] Classes: {report['names']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
