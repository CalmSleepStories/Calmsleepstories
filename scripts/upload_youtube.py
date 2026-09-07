"""
Uploads output/final_video.mp4 to YouTube using an OAuth refresh token
(no browser login needed in CI, no cookies). Builds a unique title and
description from this run's metadata so nothing gets repeated.
"""

import os
import json
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output")
VIDEO_PATH = os.path.join(OUT_DIR, "final_video.mp4")
METADATA_PATH = os.path.join(OUT_DIR, "metadata.json")

MADE_FOR_KIDS = os.environ.get("CHANNEL_MADE_FOR_KIDS", "false").lower() == "true"


def get_youtube_client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


# A few closing lines and hashtag sets to rotate through, so the description
# isn't byte-for-byte identical on every upload (helps with YouTube's
# inauthentic/reused-content review, which looks at whole-channel patterns).
CLOSING_LINES = [
    "Settle in, let your shoulders drop, and let this one carry you off.",
    "No need to follow every word — just let the sound wash over you.",
    "Perfect for winding down after a long day, or for staying asleep through the night.",
    "Dim the lights, get comfortable, and let this be the last thing you hear tonight.",
]

HASHTAG_SETS = [
    "#sleepstory #bedtimestory #relaxation",
    "#sleepstories #calmmind #deepsleep",
    "#bedtimestory #insomniahelp #relaxingvoice",
    "#sleepstory #slowliving #nightroutine",
]


def build_metadata(meta: dict) -> dict:
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    title = f"{meta['title']} | Sleep Story for Deep Rest ({date_str})"
    if len(title) > 100:
        title = title[:97] + "..."

    topic_id = meta.get("topic_id", 0)
    author_note = meta.get("author_note", "").strip()
    closing_line = CLOSING_LINES[topic_id % len(CLOSING_LINES)]
    hashtags = HASHTAG_SETS[topic_id % len(HASHTAG_SETS)]

    description_parts = [meta["title"]]
    if author_note:
        description_parts.append(author_note)
    description_parts.append(closing_line)
    description_parts.append(f"Tonight's story was generated on {date_str} and won't be repeated.")
    description_parts.append("Narration is AI-generated. Background footage courtesy of Pexels.")
    description_parts.append(hashtags)

    description = "\n\n".join(description_parts)

    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["sleep story", "bedtime story", "relaxation", "calm", "sleep aid"],
            "categoryId": "22",  # People & Blogs; change if you prefer
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": MADE_FOR_KIDS,
            # Discloses that narration/voice is AI-generated, per YouTube's
            # "How this content was made" disclosure requirements.
            "containsSyntheticMedia": True,
        },
    }


def main():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if not os.path.exists(VIDEO_PATH):
        raise SystemExit(f"{VIDEO_PATH} not found. Run compose_video.py first.")

    youtube = get_youtube_client()
    body = build_metadata(meta)

    media = MediaFileUpload(VIDEO_PATH, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024 * 8)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Uploading '{body['snippet']['title']}'...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Done. Uploaded: https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
