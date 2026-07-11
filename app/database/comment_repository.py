from app.database.database import get_connection
from app.models.comment import Comment
from app.util.logger import success


class CommentRepository:

    def __init__(self):
        self.conn = get_connection()
        self.cursor = self.conn.cursor()

    def save(self, comment: Comment):
        self.cursor.execute(
            """
            INSERT OR IGNORE INTO comments (
                comment_id,
                video_id,
                author,
                text,
                published_at,
                like_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                comment.comment_id,
                comment.video_id,
                comment.author,
                comment.text,
                comment.published_at,
                comment.like_count
            ),
        )
        self.conn.commit()

    def save_many(self, comments: list[Comment]):
        for comment in comments:
            self.save(comment)
        success(f"Saved {len(comments)} comments.") 

    def get_comments(self, video_id: str) -> list[Comment]:
        self.cursor.execute(
            """
            SELECT * FROM comments 
            WHERE video_id = ?
            """
        , (video_id,))
        rows = self.cursor.fetchall()

        return [Comment(**dict(row)) for row in rows]

    def close(self):
        self.conn.close()