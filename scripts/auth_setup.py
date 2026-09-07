"""
Run this ONCE on your own machine (not in GitHub Actions) to get a YouTube
OAuth refresh token. Put client_secrets.json (downloaded from Google Cloud
Console, OAuth client type = Desktop app) in the repo root before running.

    python scripts/auth_setup.py

It opens a browser for you to log in with the Google account that owns your
YouTube channel, then prints the refresh token. Copy that value into the
YOUTUBE_REFRESH_TOKEN GitHub Actions secret. Do NOT commit client_secrets.json.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRETS_PATH = os.path.join(ROOT, "client_secrets.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    if not os.path.exists(CLIENT_SECRETS_PATH):
        raise SystemExit(
            f"Missing {CLIENT_SECRETS_PATH}. Download it from Google Cloud Console "
            "(OAuth client, type: Desktop app) and place it in the repo root first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
    credentials = flow.run_local_server(port=0)

    print("\nSuccess! Save these as GitHub repository secrets:\n")
    print(f"YOUTUBE_CLIENT_ID={credentials.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={credentials.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
