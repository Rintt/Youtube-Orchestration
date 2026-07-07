from pydantic import BaseModel


class Video(BaseModel):
    video_id: str
    title: str
    channel: str
    description: str

    published_at: str | None = None

    view_count: int = 0

    like_count: int = 0

    comment_count: int = 0

    transcript: str = ""