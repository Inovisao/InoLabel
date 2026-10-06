"""Rastreamento quadro a quadro: sequência de imagens ou vídeo, e gravação das detecções."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.api import state as _state
from app.api.annotations.persistence import autosave
from app.api.common.errors import BadRequest, InvalidInput, NotFound
from app.api.common.schemas import Annotation
from app.api.frames.service import load_frame_paths
from app.api.inference.detections import extract_detections
from app.api.inference.schemas import TrackingDetectionResult, TrackingFrameResult, TrackingInferenceRequest
from app.core.detector import Detector


def resolve_frame_indices(indices: Optional[list[int]]) -> list[int]:
    if not _state.frame_paths:
        load_frame_paths()
    if not _state.frame_paths:
        raise NotFound("Nenhum frame carregado para processamento.")
    if indices is None:
        return list(range(len(_state.frame_paths)))
    resolved = []
    for index in indices:
        if index < 0 or index >= len(_state.frame_paths):
            raise BadRequest(f"frame_index fora do intervalo: {index}.")
        resolved.append(index)
    return resolved


def video_indices(video_path: Path, indices: Optional[list[int]]) -> list[int]:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise NotFound(f"Nao foi possivel abrir video: {video_path.name}.")
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()

    if indices is not None:
        if frame_count > 0:
            for index in indices:
                if index < 0 or index >= frame_count:
                    raise BadRequest(f"frame_index fora do intervalo: {index}.")
        return indices
    if frame_count <= 0:
        return []
    return list(range(frame_count))


def save_model_annotations(frame_index: int, detections: list[TrackingDetectionResult]) -> None:
    existing = [
        ann
        for ann in _state.annotation_store.get(frame_index, [])
        if getattr(ann, "source", "") != "model"
    ]
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        existing.append(
            Annotation(
                id=_state.next_ann_id[0],
                image_id=frame_index,
                category_id=det.class_id,
                bbox=[x1, y1, max(0.0, x2 - x1), max(0.0, y2 - y1)],
                track_id=det.track_id,
                source="model",
            )
        )
        _state.next_ann_id[0] += 1
    _state.annotation_store[frame_index] = existing
    autosave(frame_index)


def track_frame(
    *,
    frame: np.ndarray,
    frame_index: int,
    detector: Detector,
    tracker,
    session,
    confidence: float,
    frame_rate: int,
) -> TrackingFrameResult:
    img_h, img_w = frame.shape[:2]
    dets, scores, category_ids, _class_names = extract_detections(
        detector, frame, session.classes, confidence
    )
    tracks = tracker.update(dets, scores, category_ids, (img_h, img_w), (img_h, img_w))

    detections: list[TrackingDetectionResult] = []
    used_track_ids: set[int] = set()
    for category_id, track in tracks:
        track_id = int(track.track_id)
        if track_id in used_track_ids:
            continue
        used_track_ids.add(track_id)
        x1, y1, x2, y2 = (float(value) for value in track.tlbr)
        x1 = max(0.0, min(x1, float(img_w - 1)))
        x2 = max(0.0, min(x2, float(img_w - 1)))
        y1 = max(0.0, min(y1, float(img_h - 1)))
        y2 = max(0.0, min(y2, float(img_h - 1)))
        cat_id = int(category_id)
        if cat_id < 0 or cat_id >= len(session.classes):
            continue
        detections.append(
            TrackingDetectionResult(
                bbox=[x1, y1, x2, y2],
                class_id=cat_id,
                class_name=session.classes[cat_id],
                confidence=float(getattr(track, "score", 0.0)),
                track_id=track_id,
            )
        )

    return TrackingFrameResult(
        frame_index=frame_index,
        timestamp=frame_index / frame_rate,
        detections=detections,
    )


def run_image_sequence_tracking(session, req: TrackingInferenceRequest, detector, tracker, confidence):
    frame_indices = resolve_frame_indices(req.frame_indices)
    frames: list[TrackingFrameResult] = []
    for frame_index in frame_indices:
        frame_path = Path(_state.frame_paths[frame_index])
        frame = cv2.imread(str(frame_path))
        if frame is None:
            result = TrackingFrameResult(
                frame_index=frame_index,
                timestamp=frame_index / req.frame_rate,
                detections=[],
            )
        else:
            result = track_frame(
                frame=frame,
                frame_index=frame_index,
                detector=detector,
                tracker=tracker,
                session=session,
                confidence=confidence,
                frame_rate=req.frame_rate,
            )

        if req.save_annotations:
            save_model_annotations(frame_index, result.detections)
        frames.append(result)
    return frames


def run_video_tracking(session, req: TrackingInferenceRequest, detector, tracker, confidence):
    if req.save_annotations:
        raise InvalidInput("Autosave de tracking automatico ainda requer sequencia de imagens; use save_annotations=false para video.")

    video_path = Path(session.data_path)
    indices = video_indices(video_path, req.frame_indices)
    cap = cv2.VideoCapture(str(video_path))
    frames: list[TrackingFrameResult] = []
    try:
        if not cap.isOpened():
            raise NotFound(f"Nao foi possivel abrir video: {video_path.name}.")
        if indices:
            for frame_index in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok or frame is None:
                    frames.append(
                        TrackingFrameResult(
                            frame_index=frame_index,
                            timestamp=frame_index / req.frame_rate,
                            detections=[],
                        )
                    )
                    continue
                frames.append(
                    track_frame(
                        frame=frame,
                        frame_index=frame_index,
                        detector=detector,
                        tracker=tracker,
                        session=session,
                        confidence=confidence,
                        frame_rate=req.frame_rate,
                    )
                )
        else:
            frame_index = 0
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                frames.append(
                    track_frame(
                        frame=frame,
                        frame_index=frame_index,
                        detector=detector,
                        tracker=tracker,
                        session=session,
                        confidence=confidence,
                        frame_rate=req.frame_rate,
                    )
                )
                frame_index += 1
    finally:
        cap.release()
    return frames
