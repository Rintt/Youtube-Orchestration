from app.database.database import initialize_database
from app.database.video_repository import VideoRepository
from app.ingestion.search import search_videos

initialize_database()
repo = VideoRepository()

videos = search_videos("MCP servers")

repo.save_many(videos)

for video in videos:

    transcript = get_transcript(video.video_id)

    repo.update_transcript(
        video.video_id,
        transcript,
    )