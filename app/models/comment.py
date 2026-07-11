from pydantic import BaseModel


class Comment(BaseModel):
    comment_id: str
    video_id: str
    author: str
    text: str
    published_at: str
    like_count: int