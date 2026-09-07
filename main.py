"""
Runs the full daily pipeline in order:
  1. generate_script.py   -> Gemini writes the sleep-story script
  2. generate_audio.py    -> edge-tts narrates it, soft & slow
  3. fetch_background.py  -> Pexels calm background clips (deduped)
  4. compose_video.py     -> ffmpeg assembles the final video
  5. upload_youtube.py    -> uploads to YouTube with unique metadata

Any step failing stops the run (no partial/broken uploads).
"""

import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")

STEPS = [
    "generate_script.py",
    "generate_audio.py",
    "fetch_background.py",
    "compose_video.py",
    "upload_youtube.py",
]


def main():
    for step in STEPS:
        path = os.path.join(SCRIPTS_DIR, step)
        print(f"\n=== Running {step} ===")
        result = subprocess.run([sys.executable, path])
        if result.returncode != 0:
            print(f"\n{step} failed (exit code {result.returncode}). Stopping pipeline.")
            sys.exit(result.returncode)

    print("\nAll done — video generated and uploaded.")


if __name__ == "__main__":
    main()
