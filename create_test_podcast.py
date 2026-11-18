import asyncio
import os
import subprocess
import cv2
import numpy as np
import edge_tts

async def create_podcast_audio():
    print("[1/3] Generating multi-speaker interview audio...")
    dialogues = [
        ("The number one secret that nobody talks about when building a viral brand is the opening hook. Have you ever wondered why ninety percent of videos get zero views?", "en-US-ChristopherNeural"),
        ("It is entirely about curiosity gaps and speed of onset. If you do not capture attention in the first three seconds, people swipe away instantly.", "en-US-AvaNeural"),
        ("Exactly. The second key principle is narrative flow. You have to eliminate filler words, cut out the dead air, and deliver actionable value in every single sentence.", "en-US-ChristopherNeural"),
        ("That is why automated AI video repurposing is such a game changer. You can take any long interview, automatically isolate the viral moments, track the active speaker in nine by sixteen, and generate animated captions with perfect timing. It saves creators dozens of hours every week.", "en-US-AvaNeural"),
        ("The bottom line is simple: stop manually editing clips, and start scaling your content with artificial intelligence.", "en-US-ChristopherNeural")
    ]

    part_files = []
    for i, (text, voice) in enumerate(dialogues):
        part_path = f"e:/OpusClips/part_{i}.mp3"
        comm = edge_tts.Communicate(text, voice)
        await comm.save(part_path)
        part_files.append(part_path)

    # Concat audio files using ffmpeg concat demuxer
    concat_list = "e:/OpusClips/audio_list.txt"
    with open(concat_list, "w") as f:
        for p in part_files:
            f.write(f"file '{p}'\n")

    combined_mp3 = "e:/OpusClips/podcast_audio.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:a", "libmp3lame", "-q:a", "2", combined_mp3
    ], check=True, capture_output=True)

    # Clean up part files
    for p in part_files:
        if os.path.exists(p):
            os.remove(p)
    if os.path.exists(concat_list):
        os.remove(concat_list)

    return combined_mp3

def create_video_stream(audio_path: str, output_mp4: str):
    print("[2/3] Generating 1920x1080 podcast studio video stream...")
    # Get audio duration
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    duration_str = subprocess.run(probe_cmd, capture_output=True, text=True, check=True).stdout.strip()
    duration = float(duration_str)
    print(f"Total audio duration: {duration:.2f}s")

    # Generate a single 1920x1080 studio background frame with OpenCV
    w, h = 1920, 1080
    frame = np.zeros((h, w, 3), dtype=np.uint8)

    # Dark studio gradient background
    for y in range(h):
        r = int(15 + (y / h) * 20)
        g = int(18 + (y / h) * 15)
        b = int(28 + (y / h) * 25)
        frame[y, :] = [b, g, r]

    # Host Speaker Zone (Left side: center x ~ 580)
    cv2.circle(frame, (580, 420), 120, (180, 160, 140), -1)  # Head
    cv2.ellipse(frame, (580, 720), (220, 180), 0, 0, 180, (100, 60, 40), -1)  # Body
    cv2.putText(frame, "Alex (Host)", (500, 800), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    # Guest Speaker Zone (Right side: center x ~ 1340)
    cv2.circle(frame, (1340, 420), 120, (170, 150, 135), -1)  # Head
    cv2.ellipse(frame, (1340, 720), (220, 180), 0, 0, 180, (60, 80, 120), -1)  # Body
    cv2.putText(frame, "Dr. Ava (AI Founder)", (1200, 800), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    # Podcast Studio Branding text
    cv2.putText(frame, "AUTOCLIP AI PODCAST - EPISODE #42", (560, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (70, 220, 100), 3)

    bg_img_path = "e:/OpusClips/studio_bg.jpg"
    cv2.imwrite(bg_img_path, frame)

    print("[3/3] Muxing video and audio into production MP4...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_img_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration),
        output_mp4
    ]
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

    if os.path.exists(bg_img_path):
        os.remove(bg_img_path)
    print(f"Successfully generated: {output_mp4} ({os.path.getsize(output_mp4) / 1024:.1f} KB)")

if __name__ == "__main__":
    mp3 = asyncio.run(create_podcast_audio())
    create_video_stream(mp3, "e:/OpusClips/podcast_interview.mp4")
