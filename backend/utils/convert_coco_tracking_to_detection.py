#!/usr/bin/env python3
"""Converte COCO de tracking para COCO de deteccao (formato padrao)."""

import argparse
from pathlib import Path

from backend.dataset_export import export_detection_coco_json, load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Converte arquivo COCO com campos de tracking para formato de deteccao."
    )
    parser.add_argument("input", type=Path, help="Caminho do annotations.coco.json de entrada")
    parser.add_argument("output", type=Path, help="Caminho do arquivo COCO de deteccao de saida")
    parser.add_argument(
        "--only-annotated-images",
        action="store_true",
        help="Inclui apenas imagens que possuem ao menos uma anotacao.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {args.input}")

    payload = load_json(args.input)
    converted = export_detection_coco_json(
        payload,
        args.output,
        only_annotated_images=args.only_annotated_images,
    )

    print(
        "[OK] Conversao concluida: "
        f"{args.output} | imagens={len(converted['images'])} "
        f"anotacoes={len(converted['annotations'])} categorias={len(converted['categories'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
