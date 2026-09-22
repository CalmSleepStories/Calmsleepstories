"""
Downloads calm background video clips from Pexels matching the story's
visual_queries (written by generate_script.py). Prefers vertical (portrait)
clips for YouTube Shorts. Avoids reusing clips already listed in
content_plan.json's used_pexels_ids.
"""

import os
import json
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
CLIPS_DIR = os.path.join(OUT_DIR, "clips")
PLAN_PATH = os.path.join(ROOT, "content_plan.json")
METADATA_PATH = os.path.join(OUT_DIR, "metadata.json")

PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
HEADERS = {"Authorization": PEXELS_API_KEY}
MIN_DURATION_SECONDS = 8  # Shorts need fewer/longer clips; skip tiny ones


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def search_pexels_video(query: str, used_ids: set):
    # Prefer portrait (vertical) for Shorts
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers=HEADERS,
        params={
            "query": query,
            "per_page": 15,
            "orientation": "portrait",
        },
        timeout=30,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])

    for video in videos:
        if video["id"] in used_ids:
            continue
        if video.get("duration", 0) < MIN_DURATION_SECONDS:
            continue
        # Prefer highest resolution that is vertical-ish
        files = sorted(
            video["video_files"],
            key=lambda f: f.get("height", 0),
            reverse=True,
        )
        # Prefer files that are taller than wide (portrait)
        portrait_files = [f for f in files if f.get("height", 0) > f.get("width", 0)]
        if portrait_files:
            chosen = portrait_files[0]
        else:
            # Fallback to any high-res file; compose will crop to 9:16
            hd_files = [f for f in files if f.get("height", 0) >= 720]
            chosen = hd_files[0] if hd_files else files[0]
        return video["id"], chosen["link"]

    return None, None


def download(url: str, dest_path: str):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def main():
    os.makedirs(CLIPS_DIR, exist_ok=True)
    metadata = load_json(METADATA_PATH)
    plan = load_json(PLAN_PATH)

    used_ids = set(plan.get("used_pexels_ids", []))
    queries = metadata["visual_queries"]

    downloaded_paths = []
    for i, query in enumerate(queries):
        video_id, url = search_pexels_video(query, used_ids)
        if not url:
            print(f"No fresh vertical clip found for '{query}', trying fallback.")
            video_id, url = search_pexels_video("calm nature", used_ids)
        if not url:
            # Last resort: try landscape and let compose crop
            resp = requests.get(
                "https://api.pexels.com/videos/search",
                headers=HEADERS,
                params={"query": query, "per_page": 10, "orientation": "landscape"},
                timeout=30,
            )
            if resp.ok:
                for video in resp.json().get("videos", []):
                    if video["id"] in used_ids or video.get("duration", 0) < MIN_DURATION_SECONDS:
                        continue
                    files = sorted(video["video_files"], key=lambda f: f.get("width", 0), reverse=True)
                    if files:
                        video_id, url = video["id"], files[0]["link"]
                        break
        if not url:
            print(f"Skipping query '{query}', no clip available.")
            continue

        dest_path = os.path.join(CLIPS_DIR, f"clip_{i:02d}.mp4")
        print(f"Downloading clip for '{query}' (Pexels id {video_id})...")
        download(url, dest_path)
        downloaded_paths.append(dest_path)
        used_ids.add(video_id)

    if not downloaded_paths:
        raise SystemExit("No background clips could be downloaded. Aborting.")

    plan["used_pexels_ids"] = list(used_ids)
    save_json(PLAN_PATH, plan)

    with open(os.path.join(OUT_DIR, "clip_list.json"), "w", encoding="utf-8") as f:
        json.dump(downloaded_paths, f, indent=2)

    print(f"Done. Downloaded {len(downloaded_paths)} clip(s) to {CLIPS_DIR}")


if __name__ == "__main__":
    main()
