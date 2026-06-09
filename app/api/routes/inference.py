from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api import state as _state
from app.api.routes.annotations import _autosave
from app.api.schemas import (
    Annotation,
    TrackingDetectionResult,
    TrackingFrameResult,
    TrackingInferenceRequest,
    TrackingInferenceResponse,
)
from app.config import VIDEO_EXTENSIONS
from app.core.detector import Detector
from app.models import ByteTrackerArgs

router = APIRouter(prefix="/api/inference", tags=["inference"])

# Test seam and lazy dependency boundary: the real tracker imports torch/scipy
# through tracker.byte_tracker, so load it only when tracking inference runs.
MultiClassByteTracker = None


def _tracker_class():
    global MultiClassByteTracker
    if MultiClassByteTracker is None:
        from app.tracking.multiclass_byte_tracking import MultiClassByteTracker as _Tracker

        MultiClassByteTracker = _Tracker
    return MultiClassByteTracker


def _session_for_request(session_id: Optional[str]):
    if session_id:
        session = _state.get_session(session_id)
    else:
        session = _state.active_session()
    if session is None:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    if session.mode != "tracking":
        raise HTTPException(status_code=422, detail="Inferencia tracking exige sessao em mode='tracking'.")
    if session.model_path is None:
        raise HTTPException(status_code=422, detail="Modo tracking automatico exige model_path.")
    return session


def _resolve_frame_indices(indices: Optional[list[int]]) -> list[int]:
    if not _state.frame_paths:
        from app.api.routes.frames import _load_frame_paths

        _load_frame_paths()
    if not _state.frame_paths:
        raise HTTPException(status_code=404, detail="Nenhum frame carregado para processamento.")
    if indices is None:
        return list(range(len(_state.frame_paths)))
    resolved = []
    for index in indices:
        if index < 0 or index >= len(_state.frame_paths):
            raise HTTPException(status_code=400, detail=f"frame_index fora do intervalo: {index}.")
        resolved.append(index)
    return resolved


def _video_indices(video_path: Path, indices: Optional[list[int]]) -> list[int]:
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise HTTPException(status_code=404, detail=f"Nao foi possivel abrir video: {video_path.name}.")
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()

    if indices is not None:
        if frame_count > 0:
            for index in indices:
                if index < 0 or index >= frame_count:
                    raise HTTPException(status_code=400, detail=f"frame_index fora do intervalo: {index}.")
        return indices
    if frame_count <= 0:
        return []
    return list(range(frame_count))


def _scalar(value) -> float:
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    arr = np.asarray(value)
    return float(arr.reshape(-1)[0])


def _xyxy(box) -> np.ndarray:
    value = box.xyxy
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    arr = np.asarray(value, dtype=np.float32)
    return arr.reshape(-1, 4)[0].astype(np.float32)


def _class_name(names, cls_id: int, fallback_classes: list[str]) -> str:
    if isinstance(names, dict):
        raw = names.get(cls_id)
        if raw is not None:
            return str(raw)
    elif isinstance(names, list) and 0 <= cls_id < len(names):
        return str(names[cls_id])
    if 0 <= cls_id < len(fallback_classes):
        return fallback_classes[cls_id]
    return str(cls_id)


def _category_id(class_name: str, cls_id: int, classes: list[str]) -> int | None:
    for index, candidate in enumerate(classes):
        if class_name == candidate or class_name.casefold() == candidate.casefold():
            return index
    if 0 <= cls_id < len(classes):
        return cls_id
    return None


def _extract_detections(detector: Detector, frame: np.ndarray, classes: list[str], conf_threshold: float):
    results = detector.predict(frame, verbose=False, conf=conf_threshold)
    if not results:
        return [], [], [], []
    result = results[0]
    names = getattr(result, "names", {})
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        boxes = []

    dets: list[np.ndarray] = []
    scores: list[float] = []
    category_ids: list[int] = []
    class_names: list[str] = []

    for box in boxes:
        confidence = _scalar(getattr(box, "conf", 0.0))
        if confidence < conf_threshold:
            continue
        cls_id = int(_scalar(getattr(box, "cls", -1)))
        class_name = _class_name(names, cls_id, classes)
        category_id = _category_id(class_name, cls_id, classes)
        if category_id is None:
            continue
        dets.append(_xyxy(box))
        scores.append(confidence)
        category_ids.append(category_id)
        class_names.append(classes[category_id])

    return dets, scores, category_ids, class_names


def _replace_saved_model_annotations(frame_index: int, detections: list[TrackingDetectionResult]) -> None:
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
    _autosave(frame_index)


def _track_frame(
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
    dets, scores, category_ids, _class_names = _extract_detections(
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


def _run_image_sequence_tracking(session, req: TrackingInferenceRequest, detector, tracker, confidence):
    frame_indices = _resolve_frame_indices(req.frame_indices)
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
            result = _track_frame(
                frame=frame,
                frame_index=frame_index,
                detector=detector,
                tracker=tracker,
                session=session,
                confidence=confidence,
                frame_rate=req.frame_rate,
            )

        if req.save_annotations:
            _replace_saved_model_annotations(frame_index, result.detections)
        frames.append(result)
    return frames


def _run_video_tracking(session, req: TrackingInferenceRequest, detector, tracker, confidence):
    if req.save_annotations:
        raise HTTPException(
            status_code=422,
            detail="Autosave de tracking automatico ainda requer sequencia de imagens; use save_annotations=false para video.",
        )

    video_path = Path(session.data_path)
    indices = _video_indices(video_path, req.frame_indices)
    cap = cv2.VideoCapture(str(video_path))
    frames: list[TrackingFrameResult] = []
    try:
        if not cap.isOpened():
            raise HTTPException(status_code=404, detail=f"Nao foi possivel abrir video: {video_path.name}.")
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
                    _track_frame(
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
                    _track_frame(
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


def _run_tracking_inference(session, req: TrackingInferenceRequest) -> TrackingInferenceResponse:
    confidence = req.confidence_threshold if req.confidence_threshold is not None else 0.4
    detector = Detector(session.model_path)
    tracker = _tracker_class()(ByteTrackerArgs(track_thresh=confidence), frame_rate=req.frame_rate)

    if Path(session.data_path).is_file() and Path(session.data_path).suffix.lower() in VIDEO_EXTENSIONS:
        frames = _run_video_tracking(session, req, detector, tracker, confidence)
    else:
        frames = _run_image_sequence_tracking(session, req, detector, tracker, confidence)

    return TrackingInferenceResponse(
        session_id=session.session_id,
        processed_frames=len(frames),
        saved_annotations=req.save_annotations,
        frames=frames,
    )


@router.post("/tracking", response_model=TrackingInferenceResponse)
async def run_tracking_inference(req: TrackingInferenceRequest) -> TrackingInferenceResponse:
    session = _session_for_request(req.session_id)
    return await run_in_threadpool(_run_tracking_inference, session, req)
