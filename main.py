from multiprocessing.util import info
from time import time

from app.database.database import initialize_database
from app.database.video_repository import VideoRepository
from app.ingestion.search import search_videos
from app.ingestion.transcript import get_transcript
from youtube_transcript_api import (
    IpBlocked
)

from app.util.logger import warning

initialize_database()
repo = VideoRepository()

videos = search_videos("MCP servers")

repo.save_many(videos)
# try:
for video in repo.get_videos_missing_transcripts():
    if video.transcript:
        info(f"Skipping '{video.title}' (already has transcript).")
        continue
    transcript = get_transcript(video.video_id)
    #time.sleep(2)
    repo.update_transcript(
        video.video_id,
        transcript,
    )
# except IpBlocked:
#     warning("Stopping transcript ingestion because YouTube blocked requests.")