from app.database.database import get_connection

class StatsRepository:
    def __init__(self):
            self.conn = get_connection()
            self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_video_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM videos")
        return self.cursor.fetchone()[0]
    def get_channel_count(self):
        self.cursor.execute("SELECT COUNT(DISTINCT channel) FROM videos")
        return self.cursor.fetchone()[0]

    def get_transcript_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM videos WHERE transcript IS NOT NULL AND transcript != ''")
        return self.cursor.fetchone()[0]
    
    def get_comment_count(self):
        self.cursor.execute("SELECT SUM(comment_count) FROM videos;")
        return self.cursor.fetchone()[0]
    def get_latest_video(self):
        self.cursor.execute("SELECT * FROM videos ORDER BY published_at DESC LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def summary(self):
        return {
            "video_count": self.get_video_count(),
            "channel_count": self.get_channel_count(),
            "transcript_count": self.get_transcript_count(),
            "comment_count": self.get_comment_count(),      
            "latest_video": self.get_latest_video()
            }

    def close(self):
        self.conn.close()
