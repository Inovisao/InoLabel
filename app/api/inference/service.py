"""Pré-anotação por modelo no modo rastreamento: valida a sessão e monta detector e rastreador."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.api import state as _state
from app.api.common.errors import InvalidInput, NotFound
from app.api.inference.schemas import TrackingInferenceRequest, TrackingInferenceResponse
from app.api.inference.tracking import run_image_sequence_tracking, run_video_tracking
from app.config import VIDEO_EXTENSIONS
from app.core.detector import Detector
from app.models import ByteTrackerArgs


# Test seam and lazy dependency boundary: the real tracker imports torch/scipy
# through tracker.byte_tracker, so load it only when tracking inference runs.
MultiClassByteTracker = None


def _tracker_class():
    global MultiClassByteTracker
    if MultiClassByteTracker is None:
        from app.tracking.multiclass_byte_tracking import MultiClassByteTracker as _Tracker

        MultiClassByteTracker = _Tracker
    return MultiClassByteTracker


def session_for_request(session_id: Optional[str]):
    if session_id:
        session = _state.get_session(session_id)
    else:
        session = _state.active_session()
    if session is None:
        raise NotFound("Sessao nao encontrada.")
    if session.mode != "tracking":
        raise InvalidInput("Inferencia tracking exige sessao em mode='tracking'.")
    if session.model_path is None:
        raise InvalidInput("Modo tracking automatico exige model_path.")
    return session


def run_tracking_inference(session, req: TrackingInferenceRequest) -> TrackingInferenceResponse:
    confidence = req.confidence_threshold if req.confidence_threshold is not None else 0.4
    detector = Detector(session.model_path)
    tracker = _tracker_class()(ByteTrackerArgs(track_thresh=confidence), frame_rate=req.frame_rate)

    if Path(session.data_path).is_file() and Path(session.data_path).suffix.lower() in VIDEO_EXTENSIONS:
        frames = run_video_tracking(session, req, detector, tracker, confidence)
    else:
        frames = run_image_sequence_tracking(session, req, detector, tracker, confidence)

    return TrackingInferenceResponse(
        session_id=session.session_id,
        processed_frames=len(frames),
        saved_annotations=req.save_annotations,
        frames=frames,
    )
