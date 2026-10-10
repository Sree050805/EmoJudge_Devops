import uvicorn
from collections import defaultdict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cnn_emotion import analyze_frame_at, EMOTIONS

app = FastAPI(title="EmoJudge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADVICE_MAP = {
    "angry": "Witness may be defensive or hostile. Use calm, neutral questions to de-escalate.",
    "disgust": "Witness shows aversion — possibly to the topic or a person involved. Probe carefully.",
    "fear": "Witness is anxious or intimidated. Slow down, use open-ended questions to build trust.",
    "happy": "Witness appears relaxed and cooperative. Good time to ask detailed follow-up questions.",
    "sad": "Witness is distressed. Show empathy, avoid pressure, give them time to respond.",
    "surprise": "Unexpected reaction detected. The question may have caught them off guard — follow up immediately.",
    "neutral": "Witness is composed. Maintain current tone; consider probing deeper on key facts.",
}

# Emotion history per video
emotion_history: dict[str, list] = defaultdict(list)


class EmotionRequest(BaseModel):
    video_path: str
    time: float


# ── Health / Status Routes ────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "EmoJudge AI API",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "service": "emojudge-ai",
        "status": "healthy"
    }


# ── Emotion Analysis ──────────────────────────────────────────────────────────

def _deception_signal(history: list) -> str | None:
    """
    Looks at recent emotion predictions for notable expression changes.
    """

    if len(history) < 3:
        return None

    recent = history[-6:]

    emotions_seq = [
        entry["emotion"]
        for entry in recent
    ]

    # Sustained stress-associated expression
    stress_emotions = {
        "fear",
        "disgust",
        "angry"
    }

    if (
        len(recent) >= 3
        and all(
            emotion in stress_emotions
            for emotion in emotions_seq[-3:]
        )
    ):
        return (
            "⚠ Sustained stress-associated facial expressions detected."
        )

    # Sudden expression change
    if len(recent) >= 2:

        previous = recent[-2]
        current = recent[-1]

        if (
            previous["emotion"] == "neutral"
            and current["emotion"] in ("fear", "surprise")
            and current["confidence"] > 65
        ):
            return (
                "⚠ Sudden facial-expression change detected."
            )

    # Rapid expression changes
    oscillations = sum(
        1
        for i in range(1, len(emotions_seq))
        if (
            emotions_seq[i] in ("fear", "surprise", "neutral")
            and emotions_seq[i] != emotions_seq[i - 1]
        )
    )

    if oscillations >= 4:
        return (
            "⚠ Rapid changes in facial-expression classifications detected."
        )

    return None


@app.post("/analyze_emotion/")
async def analyze_emotion(req: EmotionRequest):

    result = analyze_frame_at(
        req.video_path,
        req.time
    )

    if "error" in result:

        if result["error"] == "No face detected":
            return {
                "error": "No face detected"
            }

        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )

    emotion = result["dominant_emotion"]

    confidence = round(
        result["confidence"] * 100,
        1
    )

    # Treat low-confidence classifications as neutral
    if confidence < 35:
        emotion = "neutral"

    history = emotion_history[
        req.video_path
    ]

    history.append({
        "time": req.time,
        "emotion": emotion,
        "confidence": confidence
    })

    if len(history) > 200:
        history.pop(0)

    signal = _deception_signal(
        history
    )

    return {
        "time": req.time,
        "detected_emotion": emotion,
        "confidence": confidence,
        "scores": {
            key: round(value * 100, 1)
            for key, value
            in result["scores"].items()
        },
        "advice": ADVICE_MAP.get(
            emotion,
            "No specific advice available."
        ),
        "deception_signal": signal,
        "video": req.video_path,
    }


# ── Emotion History ───────────────────────────────────────────────────────────

@app.get("/emotion_history/{video_name}")
async def get_emotion_history(
    video_name: str
):

    return {
        "video": video_name,
        "history": emotion_history.get(
            video_name,
            []
        )
    }


@app.delete("/emotion_history/{video_name}")
async def clear_history(
    video_name: str
):

    emotion_history.pop(
        video_name,
        None
    )

    return {
        "status": "cleared"
    }


# ── Start FastAPI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )