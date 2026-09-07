"""
Turns output/script.txt into a soft, slow narration track using edge-tts
(free, no API key). Splits into chunks so very long scripts don't hit
per-request limits, then stitches them together.
"""

import os
import asyncio
import subprocess

import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
SCRIPT_PATH = os.path.join(OUT_DIR, "script.txt")

VOICE = os.environ.get("TTS_VOICE", "en-US-JennyNeural")
RATE = os.environ.get("TTS_RATE", "-15%")   # slower than normal speech
PITCH = os.environ.get("TTS_PITCH", "-5Hz")  # slightly lower, softer tone
VOLUME = os.environ.get("TTS_VOLUME", "-5%")

CHUNK_CHAR_LIMIT = 3000  # keep well under edge-tts practical limits


def chunk_text(text: str, limit: int) -> list:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > limit:
            if current:
                chunks.append(current)
            current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


async def synthesize_chunk(text: str, out_path: str):
    communicate = edge_tts.Communicate(
        text, VOICE, rate=RATE, pitch=PITCH, volume=VOLUME
    )
    await communicate.save(out_path)


async def synthesize_all(chunks: list) -> list:
    paths = []
    for i, chunk in enumerate(chunks):
        out_path = os.path.join(OUT_DIR, f"narration_part_{i:03d}.mp3")
        print(f"Synthesizing part {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
        await synthesize_chunk(chunk, out_path)
        paths.append(out_path)
    return paths


def stitch_with_ffmpeg(part_paths: list, final_path: str):
    concat_list_path = os.path.join(OUT_DIR, "narration_concat.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in part_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", final_path,
    ]
    subprocess.run(cmd, check=True)


def main():
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_text = f.read()

    chunks = chunk_text(script_text, CHUNK_CHAR_LIMIT)
    print(f"Script split into {len(chunks)} chunk(s) for TTS.")

    part_paths = asyncio.run(synthesize_all(chunks))

    final_path = os.path.join(OUT_DIR, "narration.mp3")
    if len(part_paths) == 1:
        os.replace(part_paths[0], final_path)
    else:
        stitch_with_ffmpeg(part_paths, final_path)
        for p in part_paths:
            os.remove(p)

    print(f"Done. Wrote {final_path}")


if __name__ == "__main__":
    main()
