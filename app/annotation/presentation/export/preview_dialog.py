"""Preview modal de uma operacao de data augmentation."""

from __future__ import annotations

import random
import tkinter as tk
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
from PIL import Image, ImageTk

from app.annotation.core.augmentation.augmentation_service import apply_preset
from app.annotation.core.augmentation.augmentation_types import AugEntry, AugmentationPreset
from app.annotation.core.export.yolo_label_service import annotations_to_yolo_bboxes
from app.ui.theme import COLORS, FONTS, SPACING


def open_augmentation_preview_dialog(
    parent: tk.Misc,
    *,
    aug_key: str,
    aug_label: str,
    params: Dict[str, Any],
    images: List[dict],
    annotations: List[dict],
    image_root: Path,
    class_mapping: Dict[int, int],
):
    dialog = tk.Toplevel(parent)
    dialog.title(f"Preview - {aug_label}")
    dialog.configure(bg=COLORS["bg"])
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.geometry("760x520")

    title = tk.Label(
        dialog,
        text=f"Preview: {aug_label}",
        font=FONTS["heading"],
        bg=COLORS["bg"],
        fg=COLORS["text"],
        anchor="w",
    )
    title.pack(fill=tk.X, padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"]))

    preview_row = tk.Frame(dialog, bg=COLORS["bg"])
    preview_row.pack(fill=tk.BOTH, expand=True, padx=SPACING["md"], pady=SPACING["xs"])

    before_label = tk.Label(preview_row, text="Original", font=FONTS["label"], bg=COLORS["bg"], fg=COLORS["text"])
    before_label.grid(row=0, column=0, sticky="w")
    after_label = tk.Label(preview_row, text="Augmentada", font=FONTS["label"], bg=COLORS["bg"], fg=COLORS["text"])
    after_label.grid(row=0, column=1, sticky="w", padx=(SPACING["md"], 0))

    before_img = tk.Label(preview_row, bg=COLORS["canvas_bg"], width=340, height=340)
    before_img.grid(row=1, column=0, sticky="nsew")
    after_img = tk.Label(preview_row, bg=COLORS["canvas_bg"], width=340, height=340)
    after_img.grid(row=1, column=1, sticky="nsew", padx=(SPACING["md"], 0))

    status_var = tk.StringVar(value="")
    status = tk.Label(dialog, textvariable=status_var, font=FONTS["caption"], bg=COLORS["bg"], fg=COLORS["muted"])
    status.pack(fill=tk.X, padx=SPACING["md"])

    sample_state = {"image": None}

    def select_sample():
        candidates = [image for image in images if str(image.get("file_name", "")).strip()]
        sample_state["image"] = random.choice(candidates) if candidates else None
        render()

    def draw_boxes(frame: np.ndarray, boxes: List[List[Any]]) -> np.ndarray:
        output = frame.copy()
        height, width = output.shape[:2]
        for box in boxes:
            if len(box) != 5:
                continue
            cx, cy, bw, bh = (float(value) for value in box[1:5])
            x1 = int((cx - bw / 2.0) * width)
            y1 = int((cy - bh / 2.0) * height)
            x2 = int((cx + bw / 2.0) * width)
            y2 = int((cy + bh / 2.0) * height)
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 255), 2)
        return output

    def to_photo(frame: np.ndarray):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        pil.thumbnail((340, 340))
        return ImageTk.PhotoImage(pil)

    def render():
        sample = sample_state["image"]
        if sample is None:
            status_var.set("Nenhuma imagem salva disponivel para preview.")
            return
        file_name = str(sample.get("file_name", ""))
        path = image_root / file_name
        frame = cv2.imread(str(path))
        if frame is None:
            status_var.set(f"Nao foi possivel ler: {path}")
            return

        image_id = int(sample.get("id"))
        anns = [ann for ann in annotations if int(ann.get("image_id", -1)) == image_id]
        malformed: List[str] = []
        present = set()
        boxes = annotations_to_yolo_bboxes(
            anns,
            class_mapping,
            int(sample.get("width", frame.shape[1])),
            int(sample.get("height", frame.shape[0])),
            malformed,
            present,
            Path(file_name).with_suffix(".txt").name,
        )
        preset = AugmentationPreset(
            enabled=True,
            copies_per_image=1,
            entries=[AugEntry(key=aug_key, enabled=True, params=dict(params))],
        )
        augmented = apply_preset(frame, boxes, preset)
        aug_frame, aug_boxes = augmented[0] if augmented else (frame.copy(), boxes)

        before_photo = to_photo(draw_boxes(frame, boxes))
        after_photo = to_photo(draw_boxes(aug_frame, aug_boxes))
        before_img.configure(image=before_photo)
        after_img.configure(image=after_photo)
        before_img.image = before_photo
        after_img.image = after_photo
        status_var.set(f"{file_name} | caixas: {len(boxes)} -> {len(aug_boxes)}")

    actions = tk.Frame(dialog, bg=COLORS["bg"])
    actions.pack(fill=tk.X, padx=SPACING["md"], pady=SPACING["md"])
    tk.Button(
        actions,
        text="Trocar imagem",
        command=select_sample,
        font=FONTS["button"],
        bg=COLORS["neutral"],
        fg=COLORS["text"],
        activebackground=COLORS["neutral_active"],
        bd=0,
        padx=SPACING["md"],
        pady=SPACING["sm"],
    ).pack(side=tk.LEFT)
    tk.Button(
        actions,
        text="Fechar",
        command=dialog.destroy,
        font=FONTS["button"],
        bg=COLORS["primary"],
        fg=COLORS["fg_light"],
        activebackground=COLORS["primary_active"],
        bd=0,
        padx=SPACING["md"],
        pady=SPACING["sm"],
    ).pack(side=tk.RIGHT)

    select_sample()
