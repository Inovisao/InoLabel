from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = BASE_DIR / "imagens"
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
IMAGE_LIST_EXTENSIONS = (".txt", ".lst")
WEIGHTS_PATH = BASE_DIR / "models/detectarDocs.pt"
OUTPUT_DIR = BASE_DIR / "output_dataset"
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
ANNOTATIONS_PATH = OUTPUT_DIR / "annotations.coco.json"
COCO_DETECTION_EXPORT_PATH = OUTPUT_DIR / "annotations_detection.coco.json"
YOLO_DATASET_DIR = OUTPUT_DIR / "yolo_dataset"
HOMOGRAPHY_PATH = OUTPUT_DIR / "homography.json"
CONF_THRESHOLD = 0.40
TARGET_CLASSES = ["Documento"]
SAVE_RECTIFIED_FRAMES = False
MANUAL_IOU_THRESHOLD = 0.30
USE_RECTIFIED_FOR_DETECTION = True
FALLBACK_TO_ORIGINAL_IF_EMPTY = True
MAX_SAVED_FRAME_CACHE = 200
SHOW_MODEL_DETECTIONS = True
SHOW_MANUAL_DETECTIONS = True
WINDOW_MARGIN_PX = 80
WINDOW_TOP_RESERVED_PX = 240
CANVAS_PADDING_PX = 80
