from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound)
from app.util.logger import info, warning
from app.database.database import get_connection


def get_transcript(video_id: str) -> str:
    info(f"Fetching transcript for video ID '{video_id}'...")
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        
        text = " ".join(
            snippet.text
            for snippet in transcript
        )  
        info(f"Retrieved transcript ({len(text)} characters).")
        return text
    except (TranscriptsDisabled, NoTranscriptFound):
        warning(f"No transcript available for {video_id}")
        return ""
    
def update_transcript(self, video_id: str, transcript: str):
    info(f"Updating transcript for video ID '{video_id}'...")
    self.cursor.execute(
            """
            UPDATE videos
            SET transcript = ?
            WHERE video_id = ?
            """,
            (transcript, video_id),
        )
    self.conn.commit()