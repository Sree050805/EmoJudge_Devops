import cv2
import mediapipe as mp
from deepface import DeepFace
import numpy as np

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

def detect_emotion_with_mediapipe(video_path, analysis_time):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return "Error: Cannot open video"
    
    cap.set(cv2.CAP_PROP_POS_MSEC, analysis_time * 1000)  # Move to the specified time

    emotions_detected = []
    face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1)

    ret, frame = cap.read()
    if not ret:
        return "Error: Cannot read frame at given time"

    # Convert to RGB for MediaPipe
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(frame_rgb)

    if not results.multi_face_landmarks:
        return "No Face Detected"

    try:
        # Analyze emotion using DeepFace
        analysis = DeepFace.analyze(frame_rgb, actions=['emotion'], enforce_detection=False, detector_backend='opencv')
        
        if isinstance(analysis, list) and len(analysis) > 0:
            detected_emotion = analysis[0]['dominant_emotion']

            # Check distress features using MediaPipe facial landmarks
            if detected_emotion == "angry" and appears_distressed(results):
                detected_emotion = "sad"  # Reclassify as sadness

            emotions_detected.append(detected_emotion)
    except Exception as e:
        return f"Error: DeepFace analysis failed - {str(e)}"
    
    cap.release()
    face_mesh.close()
    
    return max(set(emotions_detected), key=emotions_detected.count) if emotions_detected else "No Emotion Detected"

def appears_distressed(results):
    """
    Detects distress features like furrowed brows and lip tightness using MediaPipe facial landmarks.
    """
    face_landmarks = results.multi_face_landmarks[0]

    # Get landmark positions for eyebrows and lips
    left_eyebrow = [face_landmarks.landmark[i] for i in [70, 63, 105]]  # Adjust based on eyebrow keypoints
    right_eyebrow = [face_landmarks.landmark[i] for i in [336, 296, 334]]
    upper_lip = [face_landmarks.landmark[i] for i in [13, 14, 15]]
    lower_lip = [face_landmarks.landmark[i] for i in [308, 317, 318]]

    # Check eyebrow furrowing (closer together → distress)
    left_diff = abs(left_eyebrow[0].y - left_eyebrow[1].y)
    right_diff = abs(right_eyebrow[0].y - right_eyebrow[1].y)
    
    # Check lip tightness (smaller gap → distress)
    lip_distance = abs(upper_lip[1].y - lower_lip[1].y)

    return (left_diff < 0.02 and right_diff < 0.02) or lip_distance < 0.01  # Tune threshold


