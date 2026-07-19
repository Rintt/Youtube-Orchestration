import asyncio
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.database import database
from app.models.chunk import Chunk
from app.models.comment import Comment
from app.models.video import Video


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class McpServerClientTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        database.DATABASE_PATH = Path(cls.tempdir.name) / "youtube.db"

        import server

        cls.server_module = server
        cls.port = _free_port()
        cls.url = f"http://127.0.0.1:{cls.port}/mcp"
        config = uvicorn.Config(
            server.mcp.streamable_http_app(),
            host="127.0.0.1",
            port=cls.port,
            log_level="warning",
        )
        cls.uvicorn_server = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.uvicorn_server.run, daemon=True)
        cls.thread.start()

        deadline = time.time() + 10
        while not cls.uvicorn_server.started and time.time() < deadline:
            time.sleep(0.05)
        if not cls.uvicorn_server.started:
            raise RuntimeError("Test MCP server did not start.")

    @classmethod
    def tearDownClass(cls):
        cls.uvicorn_server.should_exit = True
        cls.thread.join(timeout=10)
        cls.tempdir.cleanup()

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30) as http_client:
            async with streamable_http_client(
                self.url,
                http_client=http_client,
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments or {})

        self.assertFalse(result.isError, result.content)
        self.assertIsNotNone(result.structuredContent)
        return result.structuredContent

    async def test_lists_expected_tools(self):
        async with httpx.AsyncClient(timeout=30) as http_client:
            async with streamable_http_client(
                self.url,
                http_client=http_client,
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()

        self.assertEqual(
            {tool.name for tool in tools.tools},
            {
                "search_videos",
                "get_channel",
                "get_channel_videos",
                "get_video",
                "get_transcript",
                "get_comments",
                "search_video_transcript",
                "ingest_video",
                "get_stats",
            },
        )

    async def test_search_saves_video_and_get_video_reads_it(self):
        video = Video(
            video_id="search-video-1",
            title="Search Result",
            channel="Test Channel",
            description="A deterministic search result",
            published_at="2026-01-01T00:00:00Z",
            view_count=10,
            like_count=2,
            comment_count=1,
        )

        with patch.object(self.server_module, "search_videos", return_value=[video]):
            search = await self.call_tool(
                "search_videos",
                {"query": "test query", "max_results": 1},
            )

        self.assertEqual(search["count"], 1)
        self.assertEqual(search["videos"][0]["video_id"], "search-video-1")

        result = await self.call_tool("get_video", {"video_id": "search-video-1"})
        self.assertTrue(result["found"])
        self.assertEqual(result["video"]["title"], "Search Result")

    async def test_channel_tools(self):
        channel = {
            "channel_id": "UC_test",
            "title": "Test Channel",
            "description": "Channel description",
            "published_at": "2020-01-01T00:00:00Z",
            "uploads_playlist_id": "UU_test",
            "video_count": 5,
            "subscriber_count": 100,
            "view_count": 1000,
        }
        video = Video(
            video_id="channel-video-1",
            title="Channel Video",
            channel="Test Channel",
            description="From a channel",
            published_at="2026-01-02T00:00:00Z",
        )

        with patch.object(self.server_module, "resolve_channel", return_value=channel):
            result = await self.call_tool("get_channel", {"channel": "@test"})
        self.assertEqual(result["channel"]["channel_id"], "UC_test")

        with patch.object(self.server_module, "get_channel_videos", return_value=[video]):
            result = await self.call_tool(
                "get_channel_videos",
                {"channel": "@test", "max_results": 1},
            )
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["videos"][0]["video_id"], "channel-video-1")

    async def test_transcript_for_unknown_video_is_cached(self):
        with patch.object(
            self.server_module,
            "get_transcript",
            return_value="This is a cached transcript.",
        ) as get_transcript:
            result = await self.call_tool(
                "get_transcript",
                {"video_id": "unknown-video-1", "max_chars": 10},
            )

        self.assertEqual(result["source"], "youtube")
        self.assertTrue(result["truncated"])
        get_transcript.assert_called_once_with("unknown-video-1")

        result = await self.call_tool("get_video", {"video_id": "unknown-video-1"})
        self.assertTrue(result["found"])
        self.assertEqual(result["video"]["metrics"]["views"], 0)
        self.assertTrue(result["video"]["transcript"]["available"])

        with patch.object(self.server_module, "get_transcript") as get_transcript:
            result = await self.call_tool(
                "get_transcript",
                {"video_id": "unknown-video-1", "max_chars": 100},
            )

        self.assertEqual(result["source"], "cache")
        get_transcript.assert_not_called()

    async def test_comments_fetch_when_cache_has_too_few(self):
        comments = [
            Comment(
                comment_id="comment-1",
                video_id="comment-video-1",
                author="Author 1",
                text="First useful comment",
                published_at="2026-01-01T00:00:00Z",
                like_count=1,
            ),
            Comment(
                comment_id="comment-2",
                video_id="comment-video-1",
                author="Author 2",
                text="Second useful comment",
                published_at="2026-01-02T00:00:00Z",
                like_count=2,
            ),
        ]

        def fake_get_comments(video_id, max_comments=None):
            self.assertEqual(video_id, "comment-video-1")
            return comments[:max_comments]

        with patch.object(
            self.server_module,
            "get_comments",
            side_effect=fake_get_comments,
        ) as get_comments:
            result = await self.call_tool(
                "get_comments",
                {"video_id": "comment-video-1", "max_comments": 1},
            )
            self.assertEqual(result["count"], 1)

            result = await self.call_tool(
                "get_comments",
                {"video_id": "comment-video-1", "max_comments": 2},
            )
            self.assertEqual(result["count"], 2)

            result = await self.call_tool(
                "get_comments",
                {"video_id": "comment-video-1", "max_comments": 2},
            )
            self.assertEqual(result["source"], "cache")
            self.assertEqual(result["count"], 2)

        self.assertEqual(get_comments.call_count, 2)

    async def test_search_video_transcript_uses_cached_transcript(self):
        video = Video(
            video_id="semantic-video-1",
            title="Semantic Search Video",
            channel="Test Channel",
            description="A video with a transcript",
            published_at="2026-01-03T00:00:00Z",
            transcript="Python is often recommended to beginners because it is readable.",
        )
        chunk = Chunk(
            chunk_id="semantic-video-1_0",
            video_id="semantic-video-1",
            index=0,
            text="Python is often recommended to beginners because it is readable.",
        )

        with patch.object(self.server_module, "search_videos", return_value=[video]):
            await self.call_tool(
                "search_videos",
                {"query": "semantic test", "max_results": 1},
            )

        with patch.object(
            self.server_module,
            "_search_video_transcript_chunks",
            return_value=[(chunk, 0.82)],
        ) as search_chunks, patch.object(self.server_module, "get_transcript") as get_transcript:
            result = await self.call_tool(
                "search_video_transcript",
                {
                    "video_id": "semantic-video-1",
                    "query": "best beginner programming language",
                    "k": 3,
                },
            )

        self.assertTrue(result["found"])
        self.assertTrue(result["available"])
        self.assertEqual(result["source"], "cache")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["chunk_id"], "semantic-video-1_0")
        self.assertEqual(result["results"][0]["score"], 0.82)
        search_chunks.assert_called_once()
        get_transcript.assert_not_called()

    async def test_ingest_video_and_stats(self):
        comments = [
            Comment(
                comment_id="ingest-comment-1",
                video_id="ingest-video-1",
                author="Author",
                text="Useful ingest comment",
                published_at="2026-01-01T00:00:00Z",
                like_count=1,
            )
        ]

        with patch.object(
            self.server_module,
            "get_transcript",
            return_value="Ingested transcript",
        ), patch.object(self.server_module, "get_comments", return_value=comments):
            result = await self.call_tool("ingest_video", {"video_id": "ingest-video-1"})

        self.assertTrue(result["transcript"]["available"])
        self.assertEqual(result["comments"]["ingested"], 1)

        stats = await self.call_tool("get_stats")
        self.assertGreaterEqual(stats["videos"], 1)
        self.assertGreaterEqual(stats["transcripts"], 1)


if __name__ == "__main__":
    unittest.main()
