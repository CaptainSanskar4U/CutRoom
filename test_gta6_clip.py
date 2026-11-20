import sys
from pathlib import Path

# Setup paths
repo_root = Path(r"E:\OpusClips\gta6-clipper")
studio_root = Path(r"E:\OpusClips\Cutroom-Studio\cutroom-studio")
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(studio_root))

from cutroom import gta6_integration

print("GTA6 Clipper Integration Test Starting...")
src = Path(r"E:\OpusClips\podcast_interview.mp4")

# Sample words for 5s to 20s
words = [
    {"w": "When", "s": 5.2, "e": 5.5},
    {"w": "you", "s": 5.6, "e": 5.8},
    {"w": "look", "s": 5.9, "e": 6.2},
    {"w": "at", "s": 6.3, "e": 6.5},
    {"w": "the", "s": 6.6, "e": 6.8},
    {"w": "future", "s": 6.9, "e": 7.4},
    {"w": "of", "s": 7.5, "e": 7.7},
    {"w": "AI", "s": 7.8, "e": 8.3},
    {"w": "content,", "s": 8.4, "e": 9.0},
    {"w": "it", "s": 9.2, "e": 9.4},
    {"w": "is", "s": 9.5, "e": 9.7},
    {"w": "completely", "s": 9.8, "e": 10.4},
    {"w": "changing", "s": 10.5, "e": 11.0},
    {"w": "how", "s": 11.2, "e": 11.4},
    {"w": "creators", "s": 11.5, "e": 12.0},
    {"w": "produce", "s": 12.1, "e": 12.6},
    {"w": "viral", "s": 12.8, "e": 13.2},
    {"w": "shorts", "s": 13.3, "e": 13.8},
    {"w": "every", "s": 14.0, "e": 14.3},
    {"w": "single", "s": 14.4, "e": 14.8},
    {"w": "day.", "s": 14.9, "e": 15.5},
    {"w": "This", "s": 16.0, "e": 16.3},
    {"w": "is", "s": 16.4, "e": 16.6},
    {"w": "the", "s": 16.7, "e": 16.9},
    {"w": "game", "s": 17.0, "e": 17.4},
    {"w": "changer.", "s": 17.5, "e": 18.2}
]

clip_info = gta6_integration.generate_clip_from_video(
    src_video=src,
    start=5.0,
    end=18.5,
    hook="THE FUTURE OF AI CLIPS",
    streamer="Podcast Streamer",
    style="classic",
    layout="full",
    words=words
)

print("Generated clip successfully:")
print(clip_info)
