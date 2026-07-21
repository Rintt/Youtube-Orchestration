from app.database.database import get_connection
from app.models.video import Video


def _video_from_row(row) -> Video:
    data = dict(row)
    for key in ("title", "channel", "description", "transcript"):
        data[key] = data.get(key) or ""
    for key in ("view_count", "like_count", "comment_count"):
        data[key] = data.get(key) or 0
    return Video(**data)


class VideoRepository:

    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def save(self, video: Video):
        self.cursor.execute(
            """
            INSERT INTO videos (
                video_id,
                title,
                channel,
                description,
                published_at,
                view_count,
                like_count,
                comment_count,
                transcript
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title = excluded.title,
                channel = excluded.channel,
                description = excluded.description,
                published_at = excluded.published_at,
                view_count = excluded.view_count,
                like_count = excluded.like_count,
                comment_count = excluded.comment_count,
                transcript = COALESCE(NULLIF(excluded.transcript, ''), videos.transcript, '')
            """,
            (
                video.video_id,
                video.title,
                video.channel,
                video.description,
                video.published_at,
                video.view_count,
                video.like_count,
                video.comment_count,
                video.transcript,
            ),
        )
        self.conn.commit()

    def save_many(self, videos):
        for video in videos:
            self.save(video)

    def get_all(self) -> list[Video]:
        self.cursor.execute(
            """
            SELECT * FROM videos
            """
        )
        rows = self.cursor.fetchall()

        return [_video_from_row(row) for row in rows]

    def get_by_id(self, video_id: str) -> Video | None:
        self.cursor.execute(
            """
            SELECT * FROM videos
            WHERE video_id = ?
            """,
            (video_id,),
        )
        row = self.cursor.fetchone()
        if not row:
            return None
        return _video_from_row(row)

    def get_channels_matching(self, query: str, limit: int = 10) -> list[str]:
        query = query.strip().lower()
        if not query:
            return []

        self.cursor.execute(
            """
            SELECT DISTINCT channel
            FROM videos
            WHERE channel IS NOT NULL
            AND channel != ''
            ORDER BY channel
            """
        )
        channels = [row["channel"] for row in self.cursor.fetchall()]

        exact_matches = [
            channel for channel in channels
            if channel.lower() == query
        ]
        partial_matches = [
            channel for channel in channels
            if query in channel.lower() and channel not in exact_matches
        ]

        return (exact_matches + partial_matches)[:limit]

    def get_channel_videos(self, channel: str, limit: int | None = None) -> list[Video]:
        query = """
            SELECT *
            FROM videos
            WHERE channel = ?
            ORDER BY view_count DESC, like_count DESC, published_at DESC
        """
        params: tuple = (channel,)
        if limit is not None:
            query += " LIMIT ?"
            params = (channel, limit)

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        return [_video_from_row(row) for row in rows]

    def get_channel_top_videos_with_transcripts(
        self,
        channel: str,
        limit: int,
    ) -> list[Video]:
        self.cursor.execute(
            """
            SELECT *
            FROM videos
            WHERE channel = ?
            AND transcript IS NOT NULL
            AND transcript != ''
            ORDER BY view_count DESC, like_count DESC, published_at DESC
            LIMIT ?
            """,
            (channel, limit),
        )
        rows = self.cursor.fetchall()
        return [_video_from_row(row) for row in rows]

    def update_transcript(
        self,
        video_id: str,
        transcript: str
    ):
        self.cursor.execute(
            """
            INSERT INTO videos (
                video_id,
                title,
                channel,
                description,
                view_count,
                like_count,
                comment_count,
                transcript
            ) VALUES (?, '', '', '', 0, 0, 0, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                transcript = excluded.transcript
            """,
            (video_id, transcript),
        )
        self.conn.commit()

    def get_videos_missing_transcripts(self) -> list[Video]:
        self.cursor.execute(
            """
            SELECT *
            FROM videos
            WHERE transcript IS NULL
            OR transcript = ''
            """
        )

        rows = self.cursor.fetchall()

        return [_video_from_row(row) for row in rows]

    def close(self):
        self.conn.close()
