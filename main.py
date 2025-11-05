"""Ferramenta interativa para validar detecoes YOLO e gerar anotacoes COCO."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk
from ultralytics import YOLO

# ====== CONFIGURACOES ======
VIDEO_PATH = Path(
    "C:/Users/astma/Documents/inovisao/hungria/tracker/videos/POZ3_Thomas_green/1_2017-10-25_17-24-28_POZ3_Thomas_g1.mp4"
)
WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "best.pt"
OUTPUT_DIR = Path(__file__).resolve().parent / "output_dataset"
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
ANNOTATIONS_PATH = OUTPUT_DIR / "annotations.coco.json"
CONF_THRESHOLD = 0.60
TARGET_CLASS = "car"


@dataclass
class Detection:
    bbox_xyxy: np.ndarray
    confidence: float
    category_id: int


class AnnotationTool:
    """Controla a interface de validacao e a geracao do arquivo COCO."""

    def __init__(self):
        if not VIDEO_PATH.exists():
            raise FileNotFoundError(f"Video nao encontrado: {VIDEO_PATH}")
        if not WEIGHTS_PATH.exists():
            raise FileNotFoundError(f"Pesos nao encontrados: {WEIGHTS_PATH}")

        OUTPUT_DIR.mkdir(exist_ok=True)
        OUTPUT_IMAGES_DIR.mkdir(exist_ok=True)

        self.model = YOLO(str(WEIGHTS_PATH))
        self.cap = cv2.VideoCapture(str(VIDEO_PATH))
        if not self.cap.isOpened():
            raise RuntimeError(f"Falha ao abrir video: {VIDEO_PATH}")

        self.video_name = VIDEO_PATH.stem
        self.frame_index = 0
        self.image_id = 1
        self.annotation_id = 1

        self.current_frame = None
        self.current_detections: List[Detection] = []
        self.tk_image = None
        self.last_frame_shape: Optional[Tuple[int, int]] = None

        self.annotation_mode = True
        self.remove_mode = False
        self.manual_boxes: List[Tuple[int, int, int, int]] = []
        self.drawing_start: Optional[Tuple[int, int]] = None
        self.drawing_rect_id: Optional[int] = None
        self.canvas_image_id: Optional[int] = None

        self.images = []
        self.annotations = []
        self.categories = [{"id": 1, "name": TARGET_CLASS}]

        self.window = tk.Tk()
        self.window.title("Validador de deteccoes")
        self.window.protocol("WM_DELETE_WINDOW", self.on_quit)

        self.info_var = tk.StringVar(value="Carregando...")
        self.info_label = tk.Label(self.window, textvariable=self.info_var, font=("Arial", 12))
        self.info_label.pack(pady=10)

        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0)
        self.canvas.pack()

        buttons_frame = tk.Frame(self.window)
        buttons_frame.pack(pady=10)

        self.accept_button = tk.Button(buttons_frame, text="Validar (Enter)", command=self.on_accept, width=18)
        self.accept_button.grid(row=0, column=0, padx=5)

        self.reject_button = tk.Button(buttons_frame, text="Rejeitar (Espaco)", command=self.on_reject, width=18)
        self.reject_button.grid(row=0, column=1, padx=5)

        self.quit_button = tk.Button(buttons_frame, text="Sair (Esc)", command=self.on_quit, width=18)
        self.quit_button.grid(row=0, column=2, padx=5)

        self.annotation_button = tk.Button(
            buttons_frame, text="Modo anotacao ON (K)", command=self.toggle_annotation_mode, width=22
        )
        self.annotation_button.grid(row=0, column=3, padx=5)

        self.remove_button = tk.Button(
            buttons_frame, text="Remover anotacao OFF", command=self.toggle_remove_mode, width=22
        )
        self.remove_button.grid(row=0, column=4, padx=5)

        self.window.bind("<Return>", lambda event: self.on_accept())
        self.window.bind("<space>", lambda event: self.on_reject())
        self.window.bind("<Escape>", lambda event: self.on_quit())
        self.window.bind("k", lambda event: self.toggle_annotation_mode())
        self.window.bind("K", lambda event: self.toggle_annotation_mode())

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.load_next_frame()

    def load_next_frame(self):
        """Carrega o proximo frame do video e atualiza a tela."""
        ret, frame = self.cap.read()
        if not ret:
            self.finish_processing("Video finalizado.")
            return

        self.frame_index += 1
        self.current_frame = frame
        self.current_detections = self.run_model(frame)
        self.manual_boxes = []
        self.annotation_mode = True
        self.remove_mode = False
        self.drawing_start = None
        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None
        self.update_annotation_button()
        self.update_remove_button()
        self.update_display()

    def run_model(self, frame) -> List[Detection]:
        """Executa o modelo YOLO e filtra detecoes da classe alvo."""
        height, width = frame.shape[:2]
        detections: List[Detection] = []
        results = self.model(frame, verbose=False)
        if not results:
            return detections

        result = results[0]
        names = result.names

        for box in result.boxes:
            conf = float(box.conf)
            cls_id = int(box.cls)
            label = names.get(cls_id, str(cls_id))
            if conf < CONF_THRESHOLD or label != TARGET_CLASS:
                continue
            xyxy = box.xyxy.cpu().numpy()[0]
            xyxy[0::2] = np.clip(xyxy[0::2], 0, width - 1)
            xyxy[1::2] = np.clip(xyxy[1::2], 0, height - 1)
            detections.append(Detection(bbox_xyxy=xyxy, confidence=conf, category_id=1))

        return detections

    def draw_detections(self, frame, detections: List[Detection]):
        """Desenha as caixas detectadas no frame visivel."""
        for det in detections:
            x1, y1, x2, y2 = det.bbox_xyxy.astype(int)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{TARGET_CLASS} {det.confidence * 100:.1f}%"
            cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        return frame

    def update_display(self):
        """Renderiza o frame com deteccoes e anotacoes manuais."""
        if self.current_frame is None:
            return

        annotated = self.draw_detections(self.current_frame.copy(), self.current_detections)
        height, width = annotated.shape[:2]
        rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        self.tk_image = ImageTk.PhotoImage(image=pil_image)

        self.canvas.delete("all")
        self.canvas.config(width=width, height=height)
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        for (x1, y1, x2, y2) in self.manual_boxes:
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="yellow", width=2)

        self.last_frame_shape = (width, height)
        self.update_status()

    def build_status_message(self) -> str:
        """Gera mensagem de status para a barra de informacoes."""
        base = (
            f"Frame {self.frame_index} | Deteccoes validas (> {CONF_THRESHOLD*100:.0f}%): "
            f"{len(self.current_detections)}"
        )
        if self.last_frame_shape:
            width, height = self.last_frame_shape
            base += f" | Resolucao: {width}x{height}"
        base += f" | Modo anotacao: {'ON' if self.annotation_mode else 'OFF'}"
        base += f" | Remover anotacao: {'ON' if self.remove_mode else 'OFF'}"
        if self.manual_boxes:
            base += f" | BBoxes manuais: {len(self.manual_boxes)}"
        return base

    def update_status(self):
        """Atualiza o texto de status exibido na interface."""
        self.info_var.set(self.build_status_message())
        self.update_annotation_button()
        self.update_remove_button()

    def update_annotation_button(self):
        """Atualiza o texto do botao de modo de anotacao."""
        if hasattr(self, "annotation_button"):
            estado = "ON" if self.annotation_mode else "OFF"
            self.annotation_button.config(text=f"Modo anotacao {estado} (K)")

    def update_remove_button(self):
        """Atualiza o texto do botao de remocao."""
        if hasattr(self, "remove_button"):
            estado = "ON" if self.remove_mode else "OFF"
            self.remove_button.config(text=f"Remover anotacao {estado}")

    def toggle_annotation_mode(self):
        """Alterna o modo de anotacao manual ativado pelo atalho 'k'."""
        if self.current_frame is None:
            return

        self.annotation_mode = not self.annotation_mode
        if self.annotation_mode and self.remove_mode:
            self.remove_mode = False

        if not self.annotation_mode:
            if self.drawing_rect_id is not None:
                self.canvas.delete(self.drawing_rect_id)
                self.drawing_rect_id = None
            self.drawing_start = None
        estado_msg = "ativado" if self.annotation_mode else "desativado"
        print(f"[INFO] Modo anotacao manual {estado_msg}. Clique e arraste para desenhar caixas.")
        self.update_status()

    def toggle_remove_mode(self):
        """Alterna o modo de remocao de anotacoes."""
        if self.current_frame is None:
            return

        self.remove_mode = not self.remove_mode
        if self.remove_mode:
            if self.annotation_mode:
                self.annotation_mode = False
            if self.drawing_rect_id is not None:
                self.canvas.delete(self.drawing_rect_id)
                self.drawing_rect_id = None
            self.drawing_start = None
        else:
            if not self.annotation_mode:
                self.annotation_mode = True
        estado_msg = "ativado" if self.remove_mode else "desativado"
        print(f"[INFO] Modo remover anotacao {estado_msg}. Clique sobre uma caixa para remove-la.")
        self.update_status()

    def on_mouse_down(self, event):
        """Inicia o desenho de uma caixa manual quando em modo anotacao."""
        if self.current_frame is None:
            return

        if self.remove_mode:
            self.remove_annotation_at(event.x, event.y)
            return

        if not self.annotation_mode:
            return

        self.drawing_start = (event.x, event.y)
        self.drawing_rect_id = self.canvas.create_rectangle(
            event.x,
            event.y,
            event.x,
            event.y,
            outline="yellow",
            width=2,
            dash=(4, 2),
        )

    def on_mouse_drag(self, event):
        """Atualiza a caixa em desenho."""
        if self.remove_mode or not self.annotation_mode or self.drawing_start is None:
            return

        if self.drawing_rect_id is None:
            self.drawing_rect_id = self.canvas.create_rectangle(
                self.drawing_start[0],
                self.drawing_start[1],
                event.x,
                event.y,
                outline="yellow",
                width=2,
                dash=(4, 2),
            )
        self.canvas.coords(
            self.drawing_rect_id,
            self.drawing_start[0],
            self.drawing_start[1],
            event.x,
            event.y,
        )

    def on_mouse_up(self, event):
        """Finaliza a caixa manual e a armazena para o frame atual."""
        if self.remove_mode or not self.annotation_mode or self.drawing_start is None:
            return

        start_x, start_y = self.drawing_start
        end_x, end_y = event.x, event.y

        if self.drawing_rect_id is not None:
            self.canvas.delete(self.drawing_rect_id)
            self.drawing_rect_id = None

        self.drawing_start = None

        if self.last_frame_shape is None:
            return

        width, height = self.last_frame_shape
        x1, x2 = sorted((max(0, min(width - 1, start_x)), max(0, min(width - 1, end_x))))
        y1, y2 = sorted((max(0, min(height - 1, start_y)), max(0, min(height - 1, end_y))))

        if abs(x2 - x1) < 3 or abs(y2 - y1) < 3:
            return

        self.manual_boxes.append((int(x1), int(y1), int(x2), int(y2)))
        self.update_display()

    def remove_annotation_at(self, x: int, y: int) -> bool:
        """Remove caixa que contenha o ponto (x, y) se existir."""
        # Prioriza caixas manuais mais recentes
        for idx in range(len(self.manual_boxes) - 1, -1, -1):
            x1, y1, x2, y2 = self.manual_boxes[idx]
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.manual_boxes[idx]
                print("[INFO] Caixa manual removida.")
                self.update_display()
                return True

        # Em seguida avalia deteccoes do modelo
        for idx in range(len(self.current_detections) - 1, -1, -1):
            det = self.current_detections[idx]
            x1, y1, x2, y2 = det.bbox_xyxy.astype(int)
            if x1 <= x <= x2 and y1 <= y <= y2:
                del self.current_detections[idx]
                print("[INFO] Deteccao removida.")
                self.update_display()
                return True

        print("[INFO] Nenhuma caixa encontrada para remover.")
        return False

    def on_accept(self):
        """Persistir anotacoes quando o usuario aprova o frame."""
        if self.current_frame is None:
            return
        detections_to_save = list(self.current_detections)
        for box in self.manual_boxes:
            detections_to_save.append(
                Detection(bbox_xyxy=np.array(box, dtype=np.float32), confidence=1.0, category_id=1)
            )
        if detections_to_save:
            self.store_annotations(detections_to_save)
            self.write_annotations()
        self.load_next_frame()

    def on_reject(self):
        """Ignora o frame atual e avanca para o proximo."""
        self.load_next_frame()

    def on_quit(self):
        """Encerra o processo de anotacao."""
        self.finish_processing("Processo encerrado pelo usuario.")

    def store_annotations(self, detections: List[Detection]):
        """Adiciona as detecoes aprovadas na estrutura COCO."""
        height, width = self.current_frame.shape[:2]
        file_name = f"{self.video_name}_frame_{self.frame_index:05d}.jpg"
        image_path = OUTPUT_IMAGES_DIR / file_name
        if not cv2.imwrite(str(image_path), self.current_frame):
            raise RuntimeError(f"Falha ao salvar frame em {image_path}")

        image_info = {
            "id": self.image_id,
            "file_name": file_name,
            "width": width,
            "height": height,
        }
        self.images.append(image_info)

        for det in detections:
            x1, y1, x2, y2 = det.bbox_xyxy
            w = x2 - x1
            h = y2 - y1
            annotation = {
                "id": self.annotation_id,
                "image_id": self.image_id,
                "category_id": det.category_id,
                "bbox": [float(x1), float(y1), float(w), float(h)],
                "area": float(w * h),
                "iscrowd": 0,
                "segmentation": [],
                "score": float(det.confidence),
            }
            self.annotations.append(annotation)
            self.annotation_id += 1

        self.image_id += 1

    def write_annotations(self):
        """Grava o arquivo annotations.coco.json com as anotacoes atuais."""
        data = {
            "info": {
                "description": "Validacao manual de deteccoes",
                "version": "1.0",
                "video_source": str(VIDEO_PATH),
            },
            "licenses": [],
            "categories": self.categories,
            "images": self.images,
            "annotations": self.annotations,
        }
        with open(ANNOTATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[INFO] Anotacoes atualizadas em {ANNOTATIONS_PATH}")

    def finish_processing(self, message: str):
        """Libera recursos e encerra a interface."""
        self.cap.release()
        self.window.unbind("<Return>")
        self.window.unbind("<space>")
        self.window.unbind("<Escape>")
        self.accept_button.config(state=tk.DISABLED)
        self.reject_button.config(state=tk.DISABLED)
        self.quit_button.config(state=tk.DISABLED)
        if self.images or self.annotations:
            self.write_annotations()
        self.info_var.set(message)
        self.window.after(1500, self.window.destroy)

    def run(self):
        """Inicia o loop principal da interface Tkinter."""
        self.window.mainloop()


def main():
    try:
        tool = AnnotationTool()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    tool.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
