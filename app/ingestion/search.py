from app.models.video import Video
import html
from app.util.logger import info, success, warning, error
#import json 
from youtube_transcript_api import YouTubeTranscriptApi
from app.util.youtube_util import get_youtube_client

def search_videos(query: str, max_results: int = 10) -> list[Video]:
    youtube = get_youtube_client()
    info(f"Searching YouTube for '{query}'...")
    videos = []
    response = (
        youtube.search()
        .list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results,
        )
        .execute()
    )
    #print(json.dumps(response["items"][1], indent=4))
    for item in response["items"]:
        videos.append(
            Video(
                video_id=item["id"]["videoId"],
                title=html.unescape(item["snippet"]["title"]),
                channel=html.unescape(item["snippet"]["channelTitle"]),
                description=html.unescape(item["snippet"]["description"]),
                published_at=item["snippet"]["publishedAt"],
            )
        )
    success(f"Retrieved {len(videos)} videos.")
    video_ids = [video.video_id for video in videos]
    if not videos:
        return []
    statistics = fetch_video_statistics(video_ids)

    for video in videos:
        stats = statistics.get(video.video_id, {})

        video.view_count = stats.get("view_count", 0)
        video.like_count = stats.get("like_count", 0)
        video.comment_count = stats.get("comment_count", 0)
    return videos

def fetch_video_statistics( video_ids: list[str]) -> dict[str, dict]:
    youtube = get_youtube_client()
    info(f"Fetching statistics for {len(video_ids)} videos...")
    response = (
        youtube.videos()
        .list(
            part="statistics",
            id=",".join(video_ids),
        )
        .execute()
    )
    statistics_lookup = {}
    for item in response["items"]:
        statistics = item.get("statistics", {})
        statistics_lookup[item["id"]] = {
            "view_count": int(statistics.get("viewCount", 0)),
            "like_count": int(statistics.get("likeCount", 0)),
            "comment_count": int(statistics.get("commentCount", 0)),
    }
    success(f"Fetched statistics for {len(statistics_lookup)} videos.")
    return statistics_lookup