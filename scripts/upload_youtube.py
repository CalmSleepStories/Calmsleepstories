"""
Uploads output/final_video.mp4 to YouTube as a Short using an OAuth refresh token.
Builds full SEO title, description, tags and hashtags from metadata.
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


def build_metadata(meta: dict) -> dict:
    seo = meta.get("seo") or {}
    topic_title = meta.get("title", "Calm Sleep Story")

    # Title: prefer SEO title, fallback to topic
    title = seo.get("title") or f"{topic_title} | Calm Sleep Story"
    if len(title) > 100:
        title = title[:97] + "..."

    # Description: SEO body + hashtags at the end
    desc_body = seo.get("description") or (
        f"A calm sleep story about {topic_title.lower()}. "
        "Soft narration to help you relax and fall asleep. "
        "Follow for more peaceful Shorts."
    )
    hashtags = seo.get("hashtags") or ["#Shorts", "#SleepStory", "#Calm", "#Relaxation", "#DeepSleep"]
    # Ensure #Shorts is present
    hashtag_str = " ".join(hashtags)
    if "#Shorts" not in hashtag_str and "#shorts" not in hashtag_str.lower():
        hashtag_str = "#Shorts " + hashtag_str

    description = f"{desc_body}\n\n{hashtag_str}"

    # Backend tags
    tags = seo.get("tags") or [
        "sleep story", "calm sleep story", "bedtime story", "relaxation",
        "deep sleep", "sleep aid", "calm narration", "peaceful story",
        "fall asleep", "sleep shorts", "soft voice", "ambient sleep"
    ]
    # YouTube tags total char limit ~500; keep it safe
    tags = tags[:12]

    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": MADE_FOR_KIDS,
            # Discloses that narration/voice is AI-generated
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

    media = MediaFileUpload(
        VIDEO_PATH, mimetype="video/mp4", resumable=True, chunksize=1024 * 1024 * 8
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"Uploading Short: '{body['snippet']['title']}'...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Done. Uploaded Short: https://www.youtube.com/shorts/{video_id}")
    print(f"Watch page: https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
