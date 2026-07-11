from pydantic import BaseModel

class Chunk(BaseModel):
    chunk_id: str
    video_id: str
    index: int
    text: str