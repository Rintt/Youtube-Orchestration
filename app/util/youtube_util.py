from app.config import YOUTUBE_API_KEY
from googleapiclient.discovery import build

def get_youtube_client():
    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY,
    )
