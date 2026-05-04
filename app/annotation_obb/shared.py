"""Dependencias compartilhadas para o modo OBB."""

import math

from app.annotation.shared import *
from app.annotation_obb.geometry.obb_geometry import (
    OBBDetection,
    angle_from_mouse,
    clone_obb,
    clip_obb_to_image,
    global_to_local,
    hbb_to_obb,
    normalize_angle,
    obb_area,
    obb_to_points,
    points_to_hbb,
    validate_obb,
)
