from app.ingestion.search import get_youtube_client

def get_transcript(video_id: str) -> str:
    youtube = get_youtube_client()
    info(f"Fetching transcript for video ID '{video_id}'...")
      