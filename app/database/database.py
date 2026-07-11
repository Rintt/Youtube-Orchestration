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
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (

    comment_id TEXT PRIMARY KEY,

    video_id TEXT,

    author TEXT,

    text TEXT,

    published_at TEXT,

    like_count INTEGER,

    FOREIGN KEY(video_id) REFERENCES videos(video_id))
    """
    )
    conn.commit()
    conn.close()