import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data") / "youtube.db"

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS videos (

        video_id TEXT PRIMARY KEY,

        title TEXT,

        channel TEXT,

        description TEXT,

        published_at TEXT,

        view_count INTEGER,

        like_count INTEGER,

        comment_count INTEGER,

        transcript TEXT
                   

    )
    """)
    conn.commit()
    conn.close()