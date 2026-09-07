"""
Builds the final sleep-story video:
1. Concatenates the downloaded Pexels clips into one looped background track
   long enough to cover the full narration.
2. Mixes narration (loud) with optional looping background music (quiet).
3. Muxes video + mixed audio into output/final_video.mp4.

Everything is done with ffmpeg subprocess calls to keep the CI runner light.
"""

import os
import json
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
ASSETS_MUSIC_DIR = os.path.join(ROOT, "assets", "music")
NARRATION_PATH = os.path.join(OUT_DIR, "narration.mp3")
FINAL_PATH = os.path.join(OUT_DIR, "final_video.mp4")

MUSIC_VOLUME = os.environ.get("MUSIC_VOLUME", "0.08")  # very quiet bed under narration


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: str) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def build_looped_background(clip_paths: list, target_seconds: float, out_path: str):
    """Concatenate clips repeatedly (looping the list) until we cover target_seconds,
    then trim to exactly target_seconds."""
    concat_list_path = os.path.join(OUT_DIR, "video_concat.txt")

    clip_durations = [ffprobe_duration(p) for p in clip_paths]
    total = 0.0
    sequence = []
    i = 0
    while total < target_seconds:
        idx = i % len(clip_paths)
        sequence.append(clip_paths[idx])
        total += clip_durations[idx]
        i += 1

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in sequence:
            f.write(f"file '{os.path.abspath(p)}'\n")

    looped_full_path = os.path.join(OUT_DIR, "video_looped_full.mp4")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an",
        looped_full_path,
    ])

    # Trim to exact narration length.
    run([
        "ffmpeg", "-y", "-i", looped_full_path, "-t", str(target_seconds),
        "-c", "copy", out_path,
    ])
    os.remove(looped_full_path)


def find_music_track():
    if not os.path.isdir(ASSETS_MUSIC_DIR):
        return None
    for name in sorted(os.listdir(ASSETS_MUSIC_DIR)):
        if name.lower().endswith((".mp3", ".wav", ".m4a")):
            return os.path.join(ASSETS_MUSIC_DIR, name)
    return None


def mix_audio(narration_path: str, music_path: str, target_seconds: float, out_path: str):
    if music_path:
        run([
            "ffmpeg", "-y",
            "-i", narration_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={MUSIC_VOLUME}[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=3[aout]",
            "-map", "[aout]", "-t", str(target_seconds),
            "-c:a", "aac", "-b:a", "192k",
            out_path,
        ])
    else:
        print("No background music file found in assets/music/, using narration only.")
        run([
            "ffmpeg", "-y", "-i", narration_path, "-t", str(target_seconds),
            "-c:a", "aac", "-b:a", "192k", out_path,
        ])


def main():
    with open(os.path.join(OUT_DIR, "clip_list.json"), "r", encoding="utf-8") as f:
        clip_paths = json.load(f)

    narration_seconds = ffprobe_duration(NARRATION_PATH)
    print(f"Narration length: {narration_seconds:.1f}s")

    background_video_path = os.path.join(OUT_DIR, "video_background.mp4")
    build_looped_background(clip_paths, narration_seconds, background_video_path)

    mixed_audio_path = os.path.join(OUT_DIR, "mixed_audio.aac")
    music_path = find_music_track()
    mix_audio(NARRATION_PATH, music_path, narration_seconds, mixed_audio_path)

    run([
        "ffmpeg", "-y",
        "-i", background_video_path,
        "-i", mixed_audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "copy",
        "-shortest",
        "-movflags", "+faststart",
        FINAL_PATH,
    ])

    print(f"Done. Wrote {FINAL_PATH}")


if __name__ == "__main__":
    main()
