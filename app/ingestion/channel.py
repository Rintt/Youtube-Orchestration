import html
from urllib.parse import urlparse

from app.ingestion.search import fetch_video_statistics
from app.models.video import Video
from app.util.logger import info, success, warning
from app.util.youtube_util import get_youtube_client


def extract_channel_name(channel: str) -> str:
    channel = channel.strip()
    parsed = urlparse(channel)

    if not parsed.netloc:
        return channel

    parts = [part for part in parsed.path.split("/") if part]

    if not parts:
        return channel

    first = parts[0]

    if first.startswith("@"):
        return first

    if first in {"channel", "c", "user"} and len(parts) > 1:
        return parts[1]

    return first


def resolve_channel(channel: str) -> dict:
    youtube = get_youtube_client()
    channel_name = extract_channel_name(channel)

    info(f"Resolving YouTube channel '{channel_name}'...")

    if channel_name.startswith("UC"):
        response = (
            youtube.channels()
            .list(
                part="snippet,contentDetails,statistics",
                id=channel_name,
            )
            .execute()
        )
    elif channel_name.startswith("@"):
        response = (
            youtube.channels()
            .list(
                part="snippet,contentDetails,statistics",
                forHandle=channel_name,
            )
            .execute()
        )
    else:
        search_response = (
            youtube.search()
            .list(
                q=channel_name,
                part="snippet",
                type="channel",
                maxResults=1,
            )
            .execute()
        )

        items = search_response.get("items", [])
        if not items:
            raise ValueError(f"No channel found for '{channel}'.")

        channel_id = items[0]["snippet"]["channelId"]
        response = (
            youtube.channels()
            .list(
                part="snippet,contentDetails,statistics",
                id=channel_id,
            )
            .execute()
        )

    items = response.get("items", [])
    if not items:
        raise ValueError(f"No channel found for '{channel}'.")

    item = items[0]
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    uploads_playlist_id = (
        item.get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )

    if not uploads_playlist_id:
        raise ValueError(f"Channel '{channel}' does not expose an uploads playlist.")

    result = {
        "channel_id": item["id"],
        "title": html.unescape(snippet.get("title", "")),
        "description": html.unescape(snippet.get("description", "")),
        "published_at": snippet.get("publishedAt"),
        "uploads_playlist_id": uploads_playlist_id,
        "video_count": int(statistics.get("videoCount", 0)),
        "subscriber_count": int(statistics.get("subscriberCount", 0))
        if "subscriberCount" in statistics
        else None,
        "view_count": int(statistics.get("viewCount", 0)),
    }

    success(f"Resolved channel '{result['title']}'.")
    return result


def get_channel_videos(
    channel: str,
    max_results: int | None = None,
) -> list[Video]:
    youtube = get_youtube_client()
    channel_details = resolve_channel(channel)
    uploads_playlist_id = channel_details["uploads_playlist_id"]

    info(f"Fetching videos for channel '{channel_details['title']}'...")

    videos: list[Video] = []
    next_page_token = None

    while True:
        remaining = None if max_results is None else max_results - len(videos)
        if remaining is not None and remaining <= 0:
            break

        page_size = 50 if remaining is None else min(50, remaining)

        response = (
            youtube.playlistItems()
            .list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=page_size,
                pageToken=next_page_token,
            )
            .execute()
        )

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            resource_id = snippet.get("resourceId", {})
            video_id = resource_id.get("videoId")

            if not video_id:
                warning("Skipping playlist item without a video ID.")
                continue

            videos.append(
                Video(
                    video_id=video_id,
                    title=html.unescape(snippet.get("title", "")),
                    channel=html.unescape(
                        snippet.get("channelTitle", channel_details["title"])
                    ),
                    description=html.unescape(snippet.get("description", "")),
                    published_at=snippet.get("publishedAt"),
                )
            )

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    for start in range(0, len(videos), 50):
        batch = videos[start:start + 50]
        statistics = fetch_video_statistics([video.video_id for video in batch])

        for video in batch:
            stats = statistics.get(video.video_id, {})
            video.view_count = stats.get("view_count", 0)
            video.like_count = stats.get("like_count", 0)
            video.comment_count = stats.get("comment_count", 0)

    success(f"Retrieved {len(videos)} videos for channel '{channel_details['title']}'.")
    return videos
