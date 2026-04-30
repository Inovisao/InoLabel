"""Dependencias compartilhadas para os mixins de anotacao."""

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
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from ultralytics import YOLO

from tracker.byte_tracker import BYTETracker
from app.core.session import AnnotationSessionConfig, AnnotationTaskMode
from app.tracking import MultiClassByteTracker
from app.config import (
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
from app.geometry import (
    bbox_center,
    bbox_iou,
    clip_bbox,
    destination_size,
    order_points,
    parse_frame_number_from_name,
)
from app.models import ByteTrackerArgs, Detection
