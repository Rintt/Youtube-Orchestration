from app.database.database import get_connection
from app.models.video import Video


class VideoRepository:

    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def save(self, video: Video):
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO videos (
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

        return [Video(**dict(row)) for row in rows]
    def update_transcript(
        self,
        video_id: str,
        transcript: str
    ):
        self.cursor.execute(
            """
            UPDATE videos
            SET transcript = ?
            WHERE video_id = ?
            """,
            (transcript, video_id),
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

        return [Video(**dict(row)) for row in rows]