import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.database.database import initialize_database
from app.database.video_repository import VideoRepository
from app.database.comment_repository import CommentRepository
from app.database.stats_repository import StatsRepository
from app.ingestion.search import search_videos
from app.ingestion.channel import resolve_channel, get_channel_videos
from app.ingestion.transcript import get_transcript
from app.ingestion.comments import get_comments
from app.models.chunk import Chunk

initialize_database()

mcp = FastMCP(
    "youtube",
    instructions=(
        "YouTube data server. Search videos, fetch transcripts, "
        "get comments, and retrieve video statistics."
    ),
)


def _record_value(record, key: str) -> Any:
    if isinstance(record, dict):
        return record.get(key)
    return getattr(record, key)


def _truncate_text(text: str, max_chars: int) -> dict[str, Any]:
    truncated = text[:max_chars]
    return {
        "text": truncated,
        "length": len(text),
        "truncated": len(truncated) < len(text),
    }


def _video_payload(video) -> dict[str, Any]:
    video_id = _record_value(video, "video_id")
    description = _record_value(video, "description") or ""
    transcript = _record_value(video, "transcript") or ""
    return {
        "video_id": video_id,
        "title": _record_value(video, "title"),
        "channel": _record_value(video, "channel"),
        "description": _truncate_text(description, 800),
        "published_at": _record_value(video, "published_at"),
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "metrics": {
            "views": _record_value(video, "view_count"),
            "likes": _record_value(video, "like_count"),
            "comments": _record_value(video, "comment_count"),
        },
        "transcript": {
            "available": bool(transcript),
            "length": len(transcript),
        },
    }


def _comment_payload(comment) -> dict[str, Any]:
    return {
        "comment_id": comment.comment_id,
        "video_id": comment.video_id,
        "author": comment.author,
        "text": _truncate_text(comment.text, 1000),
        "published_at": comment.published_at,
        "like_count": comment.like_count,
    }


def _transcript_payload(
    video_id: str,
    transcript: str,
    source: str,
    max_chars: int,
    include_full_text: bool,
) -> dict[str, Any]:
    text = transcript if include_full_text else transcript[:max_chars]
    return {
        "video_id": video_id,
        "source": source,
        "available": bool(transcript),
        "length": len(transcript),
        "text": text,
        "truncated": bool(transcript) and len(text) < len(transcript),
    }


def _channel_query_candidates(channel: str) -> list[str]:
    raw = channel.strip()
    candidates = [raw]

    cleaned = raw.rstrip("/")
    if "/" in cleaned:
        parts = [part for part in cleaned.split("/") if part]
        if parts and parts[-1] == "videos":
            parts = parts[:-1]
        if parts:
            candidates.append(parts[-1])

    for candidate in list(candidates):
        if candidate.startswith("@"):
            candidates.append(candidate[1:])

    for candidate in list(candidates):
        normalized = candidate.replace("_", " ").replace("-", " ")
        candidates.append(normalized)
        lowered = normalized.lower()
        if lowered.endswith("gruppe"):
            candidates.append(normalized[:-6] + "group")
            candidates.append(normalized[:-6] + " group")

    unique = []
    seen = set()
    for candidate in candidates:
        candidate = candidate.strip()
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _search_video_transcript_chunks(
    video_id: str,
    transcript: str,
    query: str,
    k: int,
) -> list[tuple[Chunk, float]]:
    from app.embeddings.chunking import chunk_text
    from app.embeddings.embedder import Embedder
    from app.embeddings.vector_store import VectorStore

    chunks = chunk_text(video_id, transcript)
    if not chunks:
        return []

    embedder = Embedder()
    store = VectorStore(embedder)
    embeddings = embedder.embed_many([chunk.text for chunk in chunks])
    store.add(chunks, embeddings)
    return store.search(query, k=k)


@mcp.tool(name="search_videos", structured_output=True)
def tool_search_videos(query: str, max_results: int = 10) -> dict[str, Any]:
    """Search YouTube for videos matching a query.

    Args:
        query: Search query string (e.g. "MCP servers", "python tutorial")
        max_results: Maximum number of results to return (default 10)
    """
    videos = search_videos(query, max_results=max_results)
    with VideoRepository() as repo:
        repo.save_many(videos)
    return {
        "query": query,
        "requested_max_results": max_results,
        "count": len(videos),
        "videos": [_video_payload(video) for video in videos],
    }


@mcp.tool(name="get_channel", structured_output=True)
def tool_get_channel(channel: str) -> dict[str, Any]:
    """Get YouTube channel metadata from a channel URL, handle, ID, or name.

    Args:
        channel: Channel URL, handle, channel ID, or channel name
    """
    resolved = resolve_channel(channel)
    return {
        "input": channel,
        "channel": {
            "channel_id": resolved["channel_id"],
            "title": resolved["title"],
            "description": _truncate_text(resolved["description"], 1000),
            "published_at": resolved["published_at"],
            "uploads_playlist_id": resolved["uploads_playlist_id"],
            "metrics": {
                "videos": resolved["video_count"],
                "subscribers": resolved["subscriber_count"],
                "views": resolved["view_count"],
            },
            "url": f"https://www.youtube.com/channel/{resolved['channel_id']}",
        },
    }


@mcp.tool(name="get_channel_videos", structured_output=True)
def tool_get_channel_videos(
    channel: str,
    max_results: int | None = None,
) -> dict[str, Any]:
    """Get videos from a YouTube channel and save them to the database.

    Args:
        channel: Channel URL, handle, channel ID, or channel name
        max_results: Maximum number of videos to fetch. If omitted, fetches all uploads.
    """
    videos = get_channel_videos(channel, max_results=max_results)
    with VideoRepository() as repo:
        repo.save_many(videos)
    return {
        "channel": channel,
        "requested_max_results": max_results,
        "count": len(videos),
        "videos": [_video_payload(video) for video in videos],
    }


@mcp.tool(name="get_video", structured_output=True)
def tool_get_video(video_id: str) -> dict[str, Any]:
    """Get detailed information about a specific video.

    Args:
        video_id: YouTube video ID (e.g. "dQw4w9WgXcQ")
    """
    with VideoRepository() as repo:
        video = repo.get_by_id(video_id)
    if video:
        return {
            "video_id": video_id,
            "found": True,
            "video": _video_payload(video),
        }
    return {
        "video_id": video_id,
        "found": False,
        "error": f"Video '{video_id}' not found in database.",
    }


@mcp.tool(name="get_channel_top_transcripts_from_db", structured_output=True)
def tool_get_channel_top_transcripts_from_db(
    channel: str,
    top_n: int = 3,
    include_full_text: bool = False,
    max_chars: int = 4000,
    fallback_to_available_transcripts: bool = True,
) -> dict[str, Any]:
    """Get a channel's top videos and cached transcripts using only the database.

    Args:
        channel: Cached channel name, handle, or URL to match against database rows
        top_n: Number of top videos/transcripts to return
        include_full_text: Return full transcript text instead of truncating
        max_chars: Maximum transcript characters when include_full_text is false
        fallback_to_available_transcripts: If top videos lack transcripts, use next cached transcripts
    """
    top_n = max(1, min(top_n, 20))
    max_chars = max(100, min(max_chars, 50000))

    with VideoRepository() as repo:
        matched_channels = []
        for candidate in _channel_query_candidates(channel):
            for match in repo.get_channels_matching(candidate):
                if match not in matched_channels:
                    matched_channels.append(match)

        if not matched_channels:
            return {
                "source": "database",
                "channel_input": channel,
                "found": False,
                "matched_channels": [],
                "count": 0,
                "actual_top_videos": [],
                "transcript_videos": [],
                "error": f"No cached channel matched '{channel}'.",
            }

        matched_channel = matched_channels[0]
        actual_top_videos = repo.get_channel_videos(matched_channel, limit=top_n)

        if fallback_to_available_transcripts:
            transcript_videos = repo.get_channel_top_videos_with_transcripts(
                matched_channel,
                limit=top_n,
            )
        else:
            transcript_videos = [
                video for video in actual_top_videos
                if video.transcript
            ]

    return {
        "source": "database",
        "channel_input": channel,
        "found": True,
        "matched_channel": matched_channel,
        "matched_channels": matched_channels,
        "requested_top_n": top_n,
        "fallback_to_available_transcripts": fallback_to_available_transcripts,
        "actual_top_count": len(actual_top_videos),
        "actual_top_videos": [_video_payload(video) for video in actual_top_videos],
        "missing_top_transcripts": [
            _video_payload(video) for video in actual_top_videos
            if not video.transcript
        ],
        "transcript_count": len(transcript_videos),
        "transcript_videos": [
            {
                "video": _video_payload(video),
                "transcript": _transcript_payload(
                    video.video_id,
                    video.transcript,
                    source="database",
                    max_chars=max_chars,
                    include_full_text=include_full_text,
                ),
            }
            for video in transcript_videos
        ],
    }


@mcp.tool(name="get_transcript", structured_output=True)
def tool_get_transcript(
    video_id: str,
    max_chars: int = 4000,
    include_full_text: bool = False,
) -> dict[str, Any]:
    """Get the transcript for a video. Fetches from the API if not cached.

    Args:
        video_id: YouTube video ID
    """
    with VideoRepository() as repo:
        video = repo.get_by_id(video_id)
        if video and video.transcript:
            return _transcript_payload(
                video_id,
                video.transcript,
                source="cache",
                max_chars=max_chars,
                include_full_text=include_full_text,
            )

        transcript = get_transcript(video_id)
        if transcript:
            repo.update_transcript(video_id, transcript)
        else:
            return {
                "video_id": video_id,
                "source": "youtube",
                "available": False,
                "length": 0,
                "text": "",
                "truncated": False,
                "error": "No transcript available.",
            }
    return _transcript_payload(
        video_id,
        transcript,
        source="youtube",
        max_chars=max_chars,
        include_full_text=include_full_text,
    )


@mcp.tool(name="get_comments", structured_output=True)
def tool_get_comments(video_id: str, max_comments: int = 50) -> dict[str, Any]:
    """Get comments for a video. Fetches from the API if not cached.

    Args:
        video_id: YouTube video ID
        max_comments: Maximum number of comments to return (default 50)
    """
    with CommentRepository() as comment_repo:
        existing = comment_repo.get_comments(video_id, limit=max_comments)
        if len(existing) >= max_comments:
            return {
                "video_id": video_id,
                "source": "cache",
                "requested_max_comments": max_comments,
                "count": len(existing),
                "comments": [_comment_payload(comment) for comment in existing],
            }

        comments = get_comments(video_id, max_comments=max_comments)
        comment_repo.save_many(comments)
        comments = comment_repo.get_comments(video_id, limit=max_comments)
    return {
        "video_id": video_id,
        "source": "youtube",
        "requested_max_comments": max_comments,
        "count": len(comments),
        "comments": [_comment_payload(comment) for comment in comments],
    }


@mcp.tool(name="search_video_transcript", structured_output=True)
def tool_search_video_transcript(
    video_id: str,
    query: str,
    k: int = 5,
    max_chars: int = 1200,
) -> dict[str, Any]:
    """Semantically search one video's transcript for chunks relevant to a query.

    Args:
        video_id: YouTube video ID
        query: Natural-language question or search query
        k: Maximum number of transcript chunks to return
        max_chars: Maximum characters to return per chunk
    """
    k = max(1, min(k, 20))
    max_chars = max(100, min(max_chars, 4000))

    with VideoRepository() as repo:
        video = repo.get_by_id(video_id)
        if not video:
            return {
                "video_id": video_id,
                "query": query,
                "found": False,
                "count": 0,
                "results": [],
                "error": f"Video '{video_id}' not found in database.",
            }

        transcript = video.transcript
        source = "cache"
        if not transcript:
            transcript = get_transcript(video_id)
            source = "youtube"
            if transcript:
                repo.update_transcript(video_id, transcript)

    if not transcript:
        return {
            "video_id": video_id,
            "query": query,
            "found": True,
            "source": source,
            "available": False,
            "count": 0,
            "results": [],
            "error": "No transcript available.",
        }

    results = _search_video_transcript_chunks(video_id, transcript, query, k)
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "query": query,
        "found": True,
        "source": source,
        "available": True,
        "requested_k": k,
        "count": len(results),
        "results": [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.index,
                "score": score,
                "text": _truncate_text(chunk.text, max_chars),
            }
            for chunk, score in results
        ],
    }


@mcp.tool(name="ingest_video", structured_output=True)
def tool_ingest_video(video_id: str) -> dict[str, Any]:
    """Ingest a video fully: fetch transcript and comments, store in database.

    Args:
        video_id: YouTube video ID
    """
    with VideoRepository() as repo, CommentRepository() as comment_repo:
        transcript = get_transcript(video_id)
        if transcript:
            repo.update_transcript(video_id, transcript)

        comments = get_comments(video_id)
        comment_repo.save_many(comments)

    return {
        "video_id": video_id,
        "transcript": {
            "available": bool(transcript),
            "length": len(transcript),
        },
        "comments": {
            "ingested": len(comments),
        },
    }


@mcp.tool(name="get_stats", structured_output=True)
def tool_get_stats() -> dict[str, Any]:
    """Get summary statistics of the YouTube database."""
    with StatsRepository() as stats:
        summary = stats.summary()
    return {
        "videos": summary["video_count"],
        "channels": summary["channel_count"],
        "transcripts": summary["transcript_count"],
        "comments": summary["comment_count"],
        "latest_video": (
            _video_payload(summary["latest_video"])
            if summary["latest_video"]
            else None
        ),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("transport", nargs="?", default="stdio", choices=["stdio", "sse", "streamable-http"])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        mcp.settings.host = args.host
        mcp.settings.port = args.port
        config = uvicorn.Config(
            mcp.streamable_http_app(),
            host=args.host,
            port=args.port,
            log_level=mcp.settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        server.run()


if __name__ == "__main__":
    main()
