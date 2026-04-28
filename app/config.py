from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = Path("dataset")
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
IMAGE_LIST_EXTENSIONS = (".txt", ".lst")
WEIGHTS_PATH = Path("model.pt")
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUT_DATASET_PREFIX = "output_dataset"
OUTPUT_DIR = OUTPUTS_DIR / "output_dataset0_legacy"
OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
ANNOTATIONS_PATH = OUTPUT_DIR / "annotations.coco.json"
COCO_DETECTION_EXPORT_PATH = OUTPUT_DIR / "annotations_detection.coco.json"
YOLO_DATASET_DIR = OUTPUT_DIR / "yolo_dataset"
HOMOGRAPHY_PATH = OUTPUT_DIR / "homography.json"
CONF_THRESHOLD = 0.40
TARGET_CLASSES = []
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
