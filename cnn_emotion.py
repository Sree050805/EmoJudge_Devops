import cv2
import numpy as np
import mediapipe as mp
from deepface import DeepFace
from collections import deque


EMOTIONS = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral"
]


# ── MediaPipe Face Mesh ───────────────────────────────────────────────────────

mp_face_mesh = mp.solutions.face_mesh

_face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.3,
)


# Rolling smoothing buffer
_smooth_buffer = deque(maxlen=5)


# ── Landmark Analysis ─────────────────────────────────────────────────────────

def _landmark_scores(frame_rgb: np.ndarray) -> dict:

    adjustments = {
        e: 0.0 for e in EMOTIONS
    }

    try:

        results = _face_mesh.process(frame_rgb)

        if not results.multi_face_landmarks:
            return adjustments

        lm = results.multi_face_landmarks[0].landmark

        def y(i):
            return lm[i].y

        def x(i):
            return lm[i].x


        # Brow raise
        left_brow_raise = y(159) - y(70)
        right_brow_raise = y(386) - y(300)

        brow_raise = (
            left_brow_raise +
            right_brow_raise
        ) / 2


        # Brow furrow
        brow_furrow = abs(
            x(55) - x(285)
        )


        # Mouth measurements
        lip_width = abs(
            x(61) - x(291)
        )

        lip_height = abs(
            y(13) - y(14)
        )


        # Eye openness
        left_eye_open = abs(
            y(159) - y(145)
        )

        right_eye_open = abs(
            y(386) - y(374)
        )

        eye_open = (
            left_eye_open +
            right_eye_open
        ) / 2


        # ── Adjustments ─────────────────────────────────────

        if brow_raise > 0.03:

            adjustments["surprise"] += min(
                brow_raise * 2.0,
                0.15
            )

            adjustments["fear"] += min(
                brow_raise * 1.2,
                0.10
            )


        if brow_furrow < 0.06:

            adjustments["angry"] += min(
                (0.06 - brow_furrow) * 2.0,
                0.15
            )

            adjustments["disgust"] += min(
                (0.06 - brow_furrow),
                0.08
            )


        if lip_width > 0.35:

            adjustments["happy"] += min(
                (lip_width - 0.35) * 3.0,
                0.15
            )


        if lip_height < 0.01:

            adjustments["angry"] += 0.05
            adjustments["disgust"] += 0.05


        if eye_open > 0.04:

            adjustments["fear"] += min(
                (eye_open - 0.04) * 2.0,
                0.12
            )

            adjustments["surprise"] += min(
                (eye_open - 0.04) * 1.5,
                0.10
            )


    except Exception as e:

        print(
            "MediaPipe landmark error:",
            repr(e)
        )


    return adjustments


# ── DeepFace Analysis ─────────────────────────────────────────────────────────

def _deepface_scores(frame_bgr: np.ndarray) -> dict | None:

    """
    Runs DeepFace emotion analysis.

    IMPORTANT:
    OpenCV supplies BGR frames.
    DeepFace receives the original OpenCV BGR frame.

    Detector fallback:
        retinaface
        opencv
        skip
    """

    last_error = None


    # Try normal face detectors first
    for backend in (
        "retinaface",
        "opencv",
    ):

        try:

            print(
                f"Trying DeepFace detector: {backend}"
            )

            result = DeepFace.analyze(
                img_path=frame_bgr,
                actions=["emotion"],
                enforce_detection=True,
                detector_backend=backend,
                silent=True,
            )


            if isinstance(result, list):

                if not result:
                    continue

                result = result[0]


            raw = result.get(
                "emotion",
                {}
            )


            if not raw:
                continue


            total = sum(
                float(v)
                for v in raw.values()
            ) or 1.0


            scores = {
                str(k).lower():
                    float(v) / total

                for k, v in raw.items()
            }


            print(
                "DeepFace success:",
                backend,
                scores
            )


            return scores


        except Exception as e:

            last_error = e

            print(
                f"DeepFace {backend} failed:",
                repr(e)
            )


    # ── Fallback ─────────────────────────────────────────────
    #
    # Skip face detection and analyze the full frame.
    #
    # This is useful when the face detector has difficulty
    # with courtroom footage, scaling or unusual angles.

    try:

        print(
            "Trying DeepFace fallback without "
            "face enforcement..."
        )


        result = DeepFace.analyze(
            img_path=frame_bgr,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="skip",
            silent=True,
        )


        if isinstance(result, list):

            if not result:
                return None

            result = result[0]


        raw = result.get(
            "emotion",
            {}
        )


        if not raw:

            return None


        total = sum(
            float(v)
            for v in raw.values()
        ) or 1.0


        scores = {
            str(k).lower():
                float(v) / total

            for k, v in raw.items()
        }


        print(
            "DeepFace fallback success:",
            scores
        )


        return scores


    except Exception as e:

        print(
            "DeepFace final fallback failed:",
            repr(e)
        )

        if last_error:

            print(
                "Previous DeepFace error:",
                repr(last_error)
            )


        return None


# ── Score Fusion ──────────────────────────────────────────────────────────────

def _fuse_scores(
    deepface: dict,
    landmarks: dict
) -> dict:

    fused = {
        e:
            deepface.get(e, 0.0)
            +
            landmarks.get(e, 0.0)

        for e in EMOTIONS
    }


    total = sum(
        fused.values()
    ) or 1.0


    return {
        e:
            fused[e] / total

        for e in EMOTIONS
    }


# ── Temporal Smoothing ────────────────────────────────────────────────────────

def _smooth(scores: dict) -> dict:

    _smooth_buffer.append(scores)


    avg = {
        e: 0.0
        for e in EMOTIONS
    }


    weight_sum = 0.0


    for i, score_set in enumerate(
        _smooth_buffer
    ):

        weight = 0.5 ** (
            len(_smooth_buffer)
            - 1
            - i
        )


        for emotion in EMOTIONS:

            avg[emotion] += (
                score_set.get(
                    emotion,
                    0.0
                )
                *
                weight
            )


        weight_sum += weight


    return {
        e:
            avg[e] / weight_sum

        for e in EMOTIONS
    }


# ── Emotion Prediction ────────────────────────────────────────────────────────

def predict_emotion(
    frame_bgr: np.ndarray
) -> dict:

    """
    Pipeline:

    1. DeepFace receives BGR OpenCV frame
    2. MediaPipe receives RGB copy
    3. Scores are fused
    4. Temporal smoothing is applied
    """


    if frame_bgr is None:

        return {
            "error": "Invalid video frame"
        }


    if frame_bgr.size == 0:

        return {
            "error": "Empty video frame"
        }


    # ── DeepFace ─────────────────────────────────────────────

    df_scores = _deepface_scores(
        frame_bgr
    )


    if df_scores is None:

        return {
            "error":
                "Face/emotion analysis failed"
        }


    # ── MediaPipe ────────────────────────────────────────────

    frame_rgb = cv2.cvtColor(
        frame_bgr,
        cv2.COLOR_BGR2RGB
    )


    landmark_adjustments = (
        _landmark_scores(
            frame_rgb
        )
    )


    # ── Fusion ───────────────────────────────────────────────

    fused = _fuse_scores(
        df_scores,
        landmark_adjustments
    )


    smoothed = _smooth(
        fused
    )


    dominant = max(
        smoothed,
        key=smoothed.get
    )


    return {

        "dominant_emotion":
            dominant,

        "confidence":
            float(
                smoothed[dominant]
            ),

        "scores": {
            e:
                float(smoothed[e])

            for e in EMOTIONS
        },

        "raw_deepface_scores":
            df_scores,
    }


# ── Video Frame Analysis ──────────────────────────────────────────────────────

def analyze_frame_at(
    video_path: str,
    time_sec: float
) -> dict:

    """
    Extract three nearby frames:

        time - 0.5 sec
        requested time
        time + 0.5 sec

    Successful predictions are averaged.
    """


    print(
        "\nAnalyzing:",
        video_path,
        "at",
        time_sec,
        "seconds"
    )


    cap = cv2.VideoCapture(
        video_path
    )


    if not cap.isOpened():

        print(
            "Could not open video:",
            video_path
        )

        return {
            "error": "Cannot open video"
        }


    offsets = [
        -0.5,
        0.0,
        0.5
    ]


    frame_scores = []


    for offset in offsets:

        timestamp = max(
            0.0,
            float(time_sec) + offset
        )


        cap.set(
            cv2.CAP_PROP_POS_MSEC,
            timestamp * 1000
        )


        success, frame = cap.read()


        if not success or frame is None:

            print(
                "Could not read frame at:",
                timestamp
            )

            continue


        print(
            "Frame:",
            timestamp,
            "shape:",
            frame.shape
        )


        # IMPORTANT:
        # Keep the OpenCV BGR frame here.
        result = predict_emotion(
            frame
        )


        if "error" in result:

            print(
                "Frame analysis failed:",
                result["error"]
            )

            continue


        frame_scores.append(
            result["scores"]
        )


    cap.release()


    if not frame_scores:

        return {
            "error":
                "No usable face/emotion result"
        }


    # Average successful sampled frames

    avg_scores = {

        emotion:
            float(
                np.mean([
                    scores[emotion]
                    for scores
                    in frame_scores
                ])
            )

        for emotion in EMOTIONS
    }


    total = sum(
        avg_scores.values()
    ) or 1.0


    avg_scores = {

        emotion:
            avg_scores[emotion]
            / total

        for emotion in EMOTIONS
    }


    dominant = max(
        avg_scores,
        key=avg_scores.get
    )


    print(
        "Final emotion:",
        dominant
    )


    print(
        "Final confidence:",
        avg_scores[dominant]
    )


    return {

        "dominant_emotion":
            dominant,

        "confidence":
            float(
                avg_scores[dominant]
            ),

        "scores":
            avg_scores,
    }