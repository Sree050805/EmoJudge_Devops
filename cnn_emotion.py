import cv2
import numpy as np
import mediapipe as mp
from deepface import DeepFace
from collections import deque

EMOTIONS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]

# MediaPipe face mesh for landmark-based refinement
mp_face_mesh = mp.solutions.face_mesh
_face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
)

# Rolling smoothing buffer per video: stores last N emotion score dicts
_smooth_buffer: deque = deque(maxlen=5)


# ── Landmark-based micro-expression helpers ───────────────────────────────────

def _landmark_scores(frame_rgb: np.ndarray) -> dict:
    """
    Uses MediaPipe face mesh landmarks to compute micro-expression signals:
    - Brow raise → surprise/fear boost
    - Brow furrow → angry boost
    - Lip corner pull → happy boost
    - Lip press / jaw clench → angry/disgust boost
    - Eye openness → fear/surprise boost
    Returns a dict of small additive adjustments per emotion (range ~0 to 0.15).
    """
    adjustments = {e: 0.0 for e in EMOTIONS}
    results = _face_mesh.process(frame_rgb)
    if not results.multi_face_landmarks:
        return adjustments

    lm = results.multi_face_landmarks[0].landmark

    def y(i): return lm[i].y
    def x(i): return lm[i].x

    # Brow height relative to eye (higher = raised brows)
    left_brow_raise  = y(159) - y(70)   # left eye top vs left brow
    right_brow_raise = y(386) - y(300)  # right eye top vs right brow
    brow_raise = (left_brow_raise + right_brow_raise) / 2

    # Brow furrow: horizontal distance between inner brow points
    brow_furrow = abs(x(55) - x(285))

    # Lip corner pull (smile): corners vs center lip
    lip_corner_pull = ((y(61) - y(291)) ** 2) ** 0.5  # vertical diff of corners
    lip_width = abs(x(61) - x(291))
    lip_height = abs(y(13) - y(14))  # upper vs lower inner lip

    # Eye openness (vertical eye height)
    left_eye_open  = abs(y(159) - y(145))
    right_eye_open = abs(y(386) - y(374))
    eye_open = (left_eye_open + right_eye_open) / 2

    # Apply adjustments
    if brow_raise > 0.03:
        adjustments["surprise"] += min(brow_raise * 2.0, 0.15)
        adjustments["fear"]     += min(brow_raise * 1.2, 0.10)

    if brow_furrow < 0.06:
        adjustments["angry"]   += min((0.06 - brow_furrow) * 2.0, 0.15)
        adjustments["disgust"] += min((0.06 - brow_furrow) * 1.0, 0.08)

    if lip_width > 0.35:
        adjustments["happy"] += min((lip_width - 0.35) * 3.0, 0.15)

    if lip_height < 0.01:
        adjustments["angry"]   += 0.05
        adjustments["disgust"] += 0.05

    if eye_open > 0.04:
        adjustments["fear"]     += min((eye_open - 0.04) * 2.0, 0.12)
        adjustments["surprise"] += min((eye_open - 0.04) * 1.5, 0.10)

    return adjustments


# ── Core analysis ─────────────────────────────────────────────────────────────

def _deepface_scores(frame_rgb: np.ndarray) -> dict | None:
    """
    Runs DeepFace with retinaface detector (most accurate).
    Falls back to opencv if retinaface fails.
    Returns normalized score dict or None.
    """
    for backend in ("retinaface", "mtcnn", "opencv"):
        try:
            result = DeepFace.analyze(
                frame_rgb,
                actions=["emotion"],
                enforce_detection=True,
                detector_backend=backend,
                silent=True,
            )
            raw = result[0]["emotion"] if isinstance(result, list) else result["emotion"]
            total = sum(raw.values()) or 1.0
            return {k.lower(): v / total for k, v in raw.items()}
        except Exception:
            continue
    # Last resort: no enforcement
    try:
        result = DeepFace.analyze(
            frame_rgb,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv",
            silent=True,
        )
        raw = result[0]["emotion"] if isinstance(result, list) else result["emotion"]
        total = sum(raw.values()) or 1.0
        return {k.lower(): v / total for k, v in raw.items()}
    except Exception:
        return None


def _fuse_scores(deepface: dict, landmarks: dict) -> dict:
    """Adds landmark adjustments to DeepFace scores then re-normalizes."""
    fused = {e: deepface.get(e, 0.0) + landmarks.get(e, 0.0) for e in EMOTIONS}
    total = sum(fused.values()) or 1.0
    return {e: fused[e] / total for e in EMOTIONS}


def _smooth(scores: dict) -> dict:
    """Exponential moving average over the last N frames."""
    _smooth_buffer.append(scores)
    avg = {e: 0.0 for e in EMOTIONS}
    weight_sum = 0.0
    for i, s in enumerate(_smooth_buffer):
        w = 0.5 ** (len(_smooth_buffer) - 1 - i)  # more recent = higher weight
        for e in EMOTIONS:
            avg[e] += s.get(e, 0.0) * w
        weight_sum += w
    return {e: avg[e] / weight_sum for e in EMOTIONS}


def predict_emotion(frame_rgb: np.ndarray) -> dict:
    """
    Full pipeline:
      1. DeepFace (retinaface → mtcnn → opencv fallback)
      2. MediaPipe landmark micro-expression adjustments
      3. Score fusion + re-normalization
      4. Temporal smoothing (EMA over last 5 frames)
    Returns dominant_emotion, confidence, all scores.
    """
    df_scores = _deepface_scores(frame_rgb)
    if df_scores is None:
        return {"error": "No face detected"}

    lm_adj    = _landmark_scores(frame_rgb)
    fused     = _fuse_scores(df_scores, lm_adj)
    smoothed  = _smooth(fused)

    dominant  = max(smoothed, key=smoothed.get)
    return {
        "dominant_emotion":      dominant,
        "confidence":            float(smoothed[dominant]),
        "scores":                {e: float(smoothed[e]) for e in EMOTIONS},
        "raw_deepface_scores":   df_scores,
    }


def analyze_frame_at(video_path: str, time_sec: float) -> dict:
    """
    Extracts 3 nearby frames (time-0.5s, time, time+0.5s), runs predict_emotion
    on each, averages the scores for more stable results.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Cannot open video"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    offsets = [-0.5, 0.0, 0.5]
    frame_scores = []

    for offset in offsets:
        t = max(0.0, time_sec + offset)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ret, frame = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = predict_emotion(frame_rgb)
        if "error" not in result:
            frame_scores.append(result["scores"])

    cap.release()

    if not frame_scores:
        return {"error": "No face detected"}

    # Average scores across sampled frames
    avg_scores = {e: float(np.mean([s[e] for s in frame_scores])) for e in EMOTIONS}
    total = sum(avg_scores.values()) or 1.0
    avg_scores = {e: avg_scores[e] / total for e in EMOTIONS}
    dominant = max(avg_scores, key=avg_scores.get)

    return {
        "dominant_emotion": dominant,
        "confidence":       float(avg_scores[dominant]),
        "scores":           avg_scores,
    }
