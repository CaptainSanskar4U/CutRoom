import cv2
import numpy as np
from typing import Dict, Any, List, Tuple

_face_cascade = None

def get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade

def analyze_video_faces(
    video_path: str,
    start_time: float,
    end_time: float,
    sample_count: int = 8
) -> Dict[str, Any]:
    """
    High-precision active speaker & face tracking.
    Samples frames across the clip duration to determine subject center,
    cinematic eye-level headroom, and multi-speaker layout detection.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "primary_center_x": 0.5,
            "primary_center_y": 0.35,
            "is_multi_speaker": False,
            "speaker_centers": [0.5],
            "has_face": False
        }

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 1080

    cascade = get_face_cascade()
    duration = max(1.0, end_time - start_time)
    intervals = [start_time + (duration * ((k + 0.5) / float(sample_count))) for k in range(sample_count)]

    detected_centers_x = []
    detected_centers_y = []
    speaker_candidates = []
    scale = 0.25  # Downscale 4x for fast detection

    for t in intervals:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (0, 0), fx=scale, fy=scale)
        faces = cascade.detectMultiScale(small, scaleFactor=1.15, minNeighbors=4, minSize=(24, 24))

        if len(faces) > 0:
            # Sort by area descending (largest face is primary active subject)
            faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            for f in faces[:2]:
                fx, fy, fw, fh = f
                norm_x = ((fx / scale) + (fw / scale) / 2.0) / width
                norm_y = ((fy / scale) + (fh / scale) / 2.0) / height
                speaker_candidates.append(norm_x)

            primary = faces[0]
            fx, fy, fw, fh = primary
            norm_x = ((fx / scale) + (fw / scale) / 2.0) / width
            norm_y = ((fy / scale) + (fh / scale) / 2.0) / height
            detected_centers_x.append(norm_x)
            detected_centers_y.append(norm_y)

    cap.release()

    if not detected_centers_x:
        return {
            "primary_center_x": 0.5,
            "primary_center_y": 0.35,
            "is_multi_speaker": False,
            "speaker_centers": [0.5],
            "has_face": False
        }

    # Median center to reject outliers
    median_x = float(np.median(detected_centers_x))
    median_y = float(np.median(detected_centers_y))

    # Detect multi-speaker: distinct clusters on left and right
    left_spks = [s for s in speaker_candidates if s < 0.45]
    right_spks = [s for s in speaker_candidates if s > 0.55]
    is_multi = len(left_spks) >= 2 and len(right_spks) >= 2

    speaker_centers = []
    if is_multi:
        spk_l = float(np.median(left_spks))
        spk_r = float(np.median(right_spks))
        speaker_centers = [round(spk_l, 3), round(spk_r, 3)]
    else:
        speaker_centers = [round(median_x, 3)]

    return {
        "primary_center_x": round(median_x, 3),
        "primary_center_y": round(median_y, 3),
        "is_multi_speaker": is_multi,
        "speaker_centers": speaker_centers,
        "has_face": True
    }

def compute_crop_parameters(
    orig_width: int,
    orig_height: int,
    aspect_ratio: str = "9:16",
    center_x: float = 0.5,
    center_y: float = 0.35
) -> Tuple[int, int, int, int]:
    """
    Computes exact bounding box for cropping with cinematic headroom alignment.
    In vertical 9:16 video, the speaker's eyes are aligned in the upper third (35% from top).
    """
    if aspect_ratio == "9:16":
        target_aspect = 9.0 / 16.0
    elif aspect_ratio == "1:1":
        target_aspect = 1.0
    elif aspect_ratio == "4:5":
        target_aspect = 4.0 / 5.0
    elif aspect_ratio == "16:9":
        target_aspect = 16.0 / 9.0
    else:
        target_aspect = 9.0 / 16.0

    orig_aspect = orig_width / orig_height

    if orig_aspect > target_aspect:
        # Original is wider than target (e.g. 16:9 to 9:16)
        crop_h = orig_height
        crop_w = int(round(crop_h * target_aspect))
        crop_w = crop_w - (crop_w % 2)
        target_center_px = orig_width * center_x
        crop_x = int(round(target_center_px - (crop_w / 2.0)))
        crop_y = 0
        crop_x = max(0, min(orig_width - crop_w, crop_x))
    else:
        # Original is taller than target
        crop_w = orig_width
        crop_h = int(round(crop_w / target_aspect))
        crop_h = crop_h - (crop_h % 2)
        # Apply cinematic headroom: eye-level at ~35% of the frame
        target_center_py = orig_height * center_y
        crop_y = int(round(target_center_py - (crop_h * 0.35)))
        crop_x = 0
        crop_y = max(0, min(orig_height - crop_h, crop_y))

    return crop_x, crop_y, crop_w, crop_h
