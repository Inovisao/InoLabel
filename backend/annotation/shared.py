"""Dependencias compartilhadas para os mixins de anotacao (sem UI)."""

import json
import os
import shutil
import signal
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

from backend.tracker.byte_tracker import BYTETracker
from backend.core.session import AnnotationSessionConfig, AnnotationTaskMode
from backend.tracking import MultiClassByteTracker
from backend.config import (
    ANNOTATIONS_PATH,
    CANVAS_PADDING_PX,
    COCO_DETECTION_EXPORT_PATH,
    CONF_THRESHOLD,
    DATA_ROOT,
    FALLBACK_TO_ORIGINAL_IF_EMPTY,
    HOMOGRAPHY_PATH,
    IMAGE_EXTENSIONS,
    IMAGE_LIST_EXTENSIONS,
    MANUAL_IOU_THRESHOLD,
    MAX_SAVED_FRAME_CACHE,
    OUTPUT_DIR,
    OUTPUT_IMAGES_DIR,
    SAVE_RECTIFIED_FRAMES,
    SHOW_MANUAL_DETECTIONS,
    SHOW_MODEL_DETECTIONS,
    TARGET_CLASSES,
    USE_RECTIFIED_FOR_DETECTION,
    VIDEO_EXTENSIONS,
    WEIGHTS_PATH,
    WINDOW_MARGIN_PX,
    WINDOW_TOP_RESERVED_PX,
    YOLO_DATASET_DIR,
)
from backend.geometry import (
    bbox_center,
    bbox_iou,
    clip_bbox,
    destination_size,
    order_points,
    parse_frame_number_from_name,
)
from backend.models import ByteTrackerArgs, Detection
