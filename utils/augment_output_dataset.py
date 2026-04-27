"""Aplica data augmentation ao output_dataset e atualiza as anotacoes COCO."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cv2
import numpy as np

from app.config import ANNOTATIONS_PATH, COCO_DETECTION_EXPORT_PATH, OUTPUT_IMAGES_DIR
from app.dataset_export import export_detection_coco_json

BRIGHTNESS_DELTAS = (-0.10, 0.10)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera imagens augmentadas em output_dataset e atualiza annotations.coco.json."
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=ANNOTATIONS_PATH,
        help=f"Caminho do annotations.coco.json (padrao: {ANNOTATIONS_PATH})",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=OUTPUT_IMAGES_DIR,
        help=f"Pasta das imagens do dataset (padrao: {OUTPUT_IMAGES_DIR})",
    )
    parser.add_argument(
        "--rotate90",
        action="store_true",
        help="Gera variante rotacionada 90 graus no sentido horario.",
    )
    parser.add_argument(
        "--brightness",
        action="store_true",
        help="Gera variantes com brilho -10%% e +10%%.",
    )
    parser.add_argument(
        "--include-combined",
        action="store_true",
        help="Gera tambem imagens com rotacao + brilho combinados.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria gerado sem alterar arquivos.",
    )
    args = parser.parse_args()
    if not args.rotate90 and not args.brightness:
        args.rotate90 = True
        args.brightness = True
    return args


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: Dict[str, Any]):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)


def brightness_suffix(delta: float) -> str:
    percentage = int(round(abs(delta) * 100))
    direction = "plus" if delta >= 0 else "minus"
    return f"bright_{direction}_{percentage}"


def apply_brightness(image: np.ndarray, delta: float) -> np.ndarray:
    factor = 1.0 + delta
    adjusted = np.clip(image.astype(np.float32) * factor, 0, 255)
    return adjusted.astype(np.uint8)


def rotate_image_90_cw(image: np.ndarray) -> np.ndarray:
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


def rotate_bbox_90_cw(bbox: List[float], width: int, height: int) -> List[float]:
    x, y, w, h = (float(value) for value in bbox)
    new_x = float(height) - (y + h)
    new_y = x
    return [new_x, new_y, h, w]


def clip_bbox(bbox: List[float], width: int, height: int) -> List[float]:
    x, y, w, h = (float(value) for value in bbox)
    x = min(max(x, 0.0), float(width))
    y = min(max(y, 0.0), float(height))
    w = min(max(w, 0.0), float(width) - x)
    h = min(max(h, 0.0), float(height) - y)
    return [x, y, w, h]


def transform_segmentation_90_cw(segmentation: Iterable[Any], width: int, height: int) -> List[Any]:
    transformed: List[Any] = []
    for segment in segmentation:
        if not isinstance(segment, list):
            transformed.append(segment)
            continue
        new_segment: List[float] = []
        for idx in range(0, len(segment), 2):
            x = float(segment[idx])
            y = float(segment[idx + 1])
            new_x = float(height) - y
            new_y = x
            new_segment.extend([new_x, new_y])
        transformed.append(new_segment)
    return transformed


def build_transforms(args: argparse.Namespace) -> List[Tuple[str, str, Optional[float]]]:
    transforms: List[Tuple[str, str, Optional[float]]] = []
    if args.rotate90:
        transforms.append(("rot90", "rotate90", None))
    if args.brightness:
        for delta in BRIGHTNESS_DELTAS:
            transforms.append((brightness_suffix(delta), "brightness", delta))
    if args.include_combined and args.rotate90 and args.brightness:
        for delta in BRIGHTNESS_DELTAS:
            transforms.append((f"rot90_{brightness_suffix(delta)}", "rotate90_brightness", delta))
    return transforms


def derive_augmented_name(file_name: str, suffix: str) -> str:
    path = Path(file_name)
    return f"{path.stem}__aug_{suffix}{path.suffix}"


def augment_image(
    image: np.ndarray,
    transform_kind: str,
    delta: Optional[float],
) -> np.ndarray:
    if transform_kind == "rotate90":
        return rotate_image_90_cw(image)
    if transform_kind == "brightness":
        return apply_brightness(image, float(delta))
    if transform_kind == "rotate90_brightness":
        return apply_brightness(rotate_image_90_cw(image), float(delta))
    raise ValueError(f"Transformacao desconhecida: {transform_kind}")


def augment_annotation(
    annotation: Dict[str, Any],
    transform_kind: str,
    width: int,
    height: int,
) -> Tuple[List[float], int, int, List[Any]]:
    bbox = [float(value) for value in annotation.get("bbox", [0, 0, 0, 0])]
    segmentation = deepcopy(annotation.get("segmentation", []))
    if transform_kind in {"rotate90", "rotate90_brightness"}:
        bbox = rotate_bbox_90_cw(bbox, width, height)
        bbox = clip_bbox(bbox, height, width)
        segmentation = transform_segmentation_90_cw(segmentation, width, height)
        return bbox, height, width, segmentation
    bbox = clip_bbox(bbox, width, height)
    return bbox, width, height, segmentation


def main():
    args = parse_args()
    payload = load_json(args.annotations)
    images = payload.get("images", [])
    annotations = payload.get("annotations", [])
    annotations_by_image: Dict[int, List[Dict[str, Any]]] = {}
    for ann in annotations:
        image_id = int(ann.get("image_id"))
        annotations_by_image.setdefault(image_id, []).append(ann)

    transforms = build_transforms(args)
    existing_names = {str(image.get("file_name", "")).strip() for image in images}
    next_image_id = max((int(image.get("id", 0)) for image in images), default=0) + 1
    next_annotation_id = max((int(annotation.get("id", 0)) for annotation in annotations), default=0) + 1
    new_images: List[Dict[str, Any]] = []
    new_annotations: List[Dict[str, Any]] = []

    for image_info in images:
        file_name = str(image_info.get("file_name", "")).strip()
        if not file_name:
            continue
        source_image_path = args.images_dir / file_name
        if not source_image_path.exists():
            print(f"[AVISO] Imagem ausente, ignorando: {source_image_path}")
            continue

        source_image = cv2.imread(str(source_image_path))
        if source_image is None:
            print(f"[AVISO] Nao foi possivel abrir: {source_image_path}")
            continue

        width = int(image_info.get("width", source_image.shape[1]))
        height = int(image_info.get("height", source_image.shape[0]))
        image_annotations = annotations_by_image.get(int(image_info.get("id")), [])

        for suffix, transform_kind, delta in transforms:
            augmented_name = derive_augmented_name(file_name, suffix)
            if augmented_name in existing_names:
                print(f"[INFO] Augmentacao ja existe, pulando: {augmented_name}")
                continue

            augmented_image = augment_image(source_image, transform_kind, delta)
            if transform_kind in {"rotate90", "rotate90_brightness"}:
                new_width = height
                new_height = width
            else:
                new_width = width
                new_height = height

            new_image_info = deepcopy(image_info)
            new_image_info["id"] = next_image_id
            new_image_info["file_name"] = augmented_name
            new_image_info["width"] = new_width
            new_image_info["height"] = new_height
            new_images.append(new_image_info)
            existing_names.add(augmented_name)

            for annotation in image_annotations:
                new_annotation = deepcopy(annotation)
                new_annotation["id"] = next_annotation_id
                new_annotation["image_id"] = next_image_id
                new_bbox, _, _, new_segmentation = augment_annotation(annotation, transform_kind, width, height)
                new_annotation["bbox"] = new_bbox
                new_annotation["area"] = float(new_bbox[2] * new_bbox[3])
                new_annotation["segmentation"] = new_segmentation
                new_annotations.append(new_annotation)
                next_annotation_id += 1

            if args.dry_run:
                print(f"[DRY-RUN] Geraria {augmented_name}")
            else:
                output_path = args.images_dir / augmented_name
                if not cv2.imwrite(str(output_path), augmented_image):
                    raise RuntimeError(f"Falha ao salvar imagem augmentada em {output_path}")
            next_image_id += 1

    if args.dry_run:
        print(
            f"[DRY-RUN] Imagens novas: {len(new_images)} | "
            f"Anotacoes novas: {len(new_annotations)}"
        )
        return

    payload["images"] = images + new_images
    payload["annotations"] = annotations + new_annotations
    info = payload.setdefault("info", {})
    info["augmentation"] = {
        "rotate90": args.rotate90,
        "brightness_deltas": list(BRIGHTNESS_DELTAS) if args.brightness else [],
        "include_combined": args.include_combined,
        "generated_images": len(new_images),
        "generated_annotations": len(new_annotations),
    }
    save_json(args.annotations, payload)
    print(
        f"[INFO] annotations.coco.json atualizado: "
        f"+{len(new_images)} imagens, +{len(new_annotations)} anotacoes."
    )

    if COCO_DETECTION_EXPORT_PATH.exists():
        export_detection_coco_json(payload, COCO_DETECTION_EXPORT_PATH)
        print(f"[INFO] COCO de deteccao atualizado em {COCO_DETECTION_EXPORT_PATH}")


if __name__ == "__main__":
    main()
