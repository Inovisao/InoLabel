#!/usr/bin/env python3
"""Converte um dataset COCO em um dataset YOLO com data.yaml."""

import argparse
from pathlib import Path

from app.dataset_export import export_yolo_dataset, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte annotations.coco.json em dataset YOLO com data.yaml."
    )
    parser.add_argument("input", type=Path, help="Caminho do arquivo .coco.json de entrada")
    parser.add_argument(
        "--image-root",
        type=Path,
        default=None,
        help="Diretorio das imagens referenciadas no COCO. Padrao: <pasta do coco>/images",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Diretorio de saida do dataset YOLO. Padrao: <pasta do coco>/yolo_dataset",
    )
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Proporcao para train")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Proporcao para val")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Proporcao para test")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {args.input}")

    image_root = args.image_root or (args.input.parent / "images")
    output_root = args.output_root or (args.input.parent / "yolo_dataset")

    payload = load_json(args.input)
    report = export_yolo_dataset(
        payload,
        source_images_dir=image_root,
        dataset_root=output_root,
        split_ratios=(args.train_ratio, args.val_ratio, args.test_ratio),
    )

    print(f"[OK] Dataset YOLO exportado em: {report['dataset_root']}")
    print(f"[OK] data.yaml: {report['data_yaml']}")
    print(f"[INFO] Imagens por split: {report['images_per_split']}")
    print(f"[INFO] Labels por split: {report['labels_per_split']}")
    print(f"[INFO] Classes presentes: {report['classes_present']}")
    if report["images_without_annotation"]:
        print(f"[AVISO] Imagens sem anotacao: {len(report['images_without_annotation'])}")
    if report["malformed_labels"]:
        print(f"[AVISO] Labels mal formatados ignorados: {len(report['malformed_labels'])}")
        for issue in report["malformed_labels"][:10]:
            print(f"  - {issue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
