from app.config import YOUTUBE_API_KEY
from googleapiclient.discovery import build

def get_youtube_client():
    if not YOUTUBE_API_KEY:
        raise RuntimeError(
            "YOUTUBE_API_KEY is not set. Add it to your .env file or environment."
        )

    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY,
    )
