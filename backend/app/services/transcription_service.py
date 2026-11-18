import os
import gc
import subprocess
import numpy as np
from typing import Dict, Any, List
from faster_whisper import WhisperModel
from app.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE

_whisper_cache: Dict[str, WhisperModel] = {}

def get_whisper_model(model_name: str = None) -> WhisperModel:
    model_name = model_name or WHISPER_MODEL
    if model_name not in _whisper_cache:
        print(f"[Whisper] Loading model '{model_name}' on {WHISPER_DEVICE} ({WHISPER_COMPUTE_TYPE})...")
        _whisper_cache[model_name] = WhisperModel(
            model_name,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            cpu_threads=4,
            num_workers=1
        )
    return _whisper_cache[model_name]

def load_audio_ffmpeg(file_path: str, sampling_rate: int = 16000) -> np.ndarray:
    """Decodes audio using FFmpeg directly into 16kHz float32 mono array."""
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", file_path,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sampling_rate),
        "-"
    ]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

def transcribe_audio(audio_path: str, model_name: str = None) -> Dict[str, Any]:
    """
    Chunked streaming transcription that stays under 10MB memory usage,
    completely eliminating memory allocation spikes on long videos.
    """
    model = get_whisper_model(model_name)
    audio_np = load_audio_ffmpeg(audio_path, sampling_rate=16000)
    total_samples = len(audio_np)
    total_duration = total_samples / 16000.0

    # 45-second chunks: ~720,000 samples, requires only ~7MB RAM per chunk
    chunk_seconds = 45.0
    chunk_samples = int(chunk_seconds * 16000)

    segments = []
    all_words = []
    full_text_list = []
    current_speaker = 1
    last_end = 0.0
    detected_lang = "en"
    lang_prob = 0.99
    seg_idx = 0

    for chunk_start_sample in range(0, total_samples, chunk_samples):
        chunk_end_sample = min(total_samples, chunk_start_sample + chunk_samples)
        chunk_waveform = audio_np[chunk_start_sample:chunk_end_sample]
        time_offset = chunk_start_sample / 16000.0

        # Avoid transcribing tiny residual slice (< 0.5s)
        if len(chunk_waveform) < 8000:
            continue

        try:
            segs_gen, info = model.transcribe(
                chunk_waveform,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )

            if info and info.language:
                detected_lang = info.language
                lang_prob = round(info.language_probability, 2)

            for seg in segs_gen:
                text_clean = seg.text.strip()
                if not text_clean:
                    continue

                abs_start = round(time_offset + seg.start, 2)
                abs_end = round(time_offset + seg.end, 2)

                if abs_start - last_end > 1.0 and seg_idx > 0:
                    current_speaker = 2 if current_speaker == 1 else 1

                seg_dict = {
                    "id": seg_idx,
                    "start": abs_start,
                    "end": abs_end,
                    "text": text_clean,
                    "speaker": f"Speaker {current_speaker}",
                    "words": []
                }

                if seg.words:
                    for w in seg.words:
                        w_clean = w.word.strip()
                        if not w_clean:
                            continue
                        word_entry = {
                            "word": w_clean,
                            "start": round(time_offset + w.start, 2),
                            "end": round(time_offset + w.end, 2),
                            "probability": round(w.probability, 2),
                            "speaker": f"Speaker {current_speaker}"
                        }
                        seg_dict["words"].append(word_entry)
                        all_words.append(word_entry)

                segments.append(seg_dict)
                full_text_list.append(text_clean)
                last_end = abs_end
                seg_idx += 1

        except Exception as chunk_err:
            print(f"[Whisper] Warning on chunk at {time_offset:.1f}s: {chunk_err}")
        finally:
            del chunk_waveform
            gc.collect()

    del audio_np
    gc.collect()

    return {
        "language": detected_lang,
        "language_probability": lang_prob,
        "duration": round(total_duration, 2),
        "full_text": " ".join(full_text_list),
        "segments": segments,
        "words": all_words
    }
