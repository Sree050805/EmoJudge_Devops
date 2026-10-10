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
    "angry":    "Witness may be defensive or hostile. Use calm, neutral questions to de-escalate.",
    "disgust":  "Witness shows aversion — possibly to the topic or a person involved. Probe carefully.",
    "fear":     "Witness is anxious or intimidated. Slow down, use open-ended questions to build trust.",
    "happy":    "Witness appears relaxed and cooperative. Good time to ask detailed follow-up questions.",
    "sad":      "Witness is distressed. Show empathy, avoid pressure, give them time to respond.",
    "surprise": "Unexpected reaction detected. The question may have caught them off guard — follow up immediately.",
    "neutral":  "Witness is composed. Maintain current tone; consider probing deeper on key facts.",
}

# Emotion history per video
emotion_history: dict[str, list] = defaultdict(list)


class EmotionRequest(BaseModel):
    video_path: str
    time: float


def _deception_signal(history: list) -> str | None:
    """
    Looks at the last 6 entries for patterns that may indicate stress/deception:
    - Rapid oscillation between neutral and fear/surprise
    - Sustained fear or disgust (3+ consecutive)
    - Sudden spike from neutral to high-confidence fear/surprise
    """
    if len(history) < 3:
        return None

    recent = history[-6:]
    emotions_seq = [e["emotion"] for e in recent]
    confs = [e["confidence"] for e in recent]

    # Sustained negative emotion
    stress_emotions = {"fear", "disgust", "angry"}
    if len(recent) >= 3 and all(e in stress_emotions for e in emotions_seq[-3:]):
        return "⚠ Sustained stress detected — witness may be under significant pressure."

    # Sudden spike: neutral → fear/surprise with high confidence
    if len(recent) >= 2:
        prev, curr = recent[-2], recent[-1]
        if prev["emotion"] == "neutral" and curr["emotion"] in ("fear", "surprise") and curr["confidence"] > 65:
            return "⚠ Sudden emotional spike after neutral state — possible reaction to a sensitive topic."

    # Rapid oscillation (neutral ↔ fear/surprise alternating)
    oscillations = sum(
        1 for i in range(1, len(emotions_seq))
        if emotions_seq[i] in ("fear", "surprise", "neutral")
        and emotions_seq[i] != emotions_seq[i - 1]
    )
    if oscillations >= 4:
        return "⚠ Emotional instability detected — witness may be concealing information."

    return None


@app.post("/analyze_emotion/")
async def analyze_emotion(req: EmotionRequest):
    result = analyze_frame_at(req.video_path, req.time)

    if "error" in result:
        if result["error"] == "No face detected":
            return {"error": "No face detected"}
        raise HTTPException(status_code=400, detail=result["error"])

    # Gate on confidence — if below 35% the model is uncertain, flag it
    emotion = result["dominant_emotion"]
    confidence = round(result["confidence"] * 100, 1)
    if confidence < 35:
        emotion = "neutral"  # treat low-confidence as neutral rather than wrong label

    history = emotion_history[req.video_path]
    history.append({"time": req.time, "emotion": emotion, "confidence": confidence})
    if len(history) > 200:
        history.pop(0)

    deception = _deception_signal(history)

    return {
        "time":             req.time,
        "detected_emotion": emotion,
        "confidence":       confidence,
        "scores":           {k: round(v * 100, 1) for k, v in result["scores"].items()},
        "advice":           ADVICE_MAP.get(emotion, "No specific advice available."),
        "deception_signal": deception,
        "video":            req.video_path,
    }


@app.get("/emotion_history/{video_name}")
async def get_emotion_history(video_name: str):
    return {"video": video_name, "history": emotion_history.get(video_name, [])}


@app.delete("/emotion_history/{video_name}")
async def clear_history(video_name: str):
    emotion_history.pop(video_name, None)
    return {"status": "cleared"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
