

from app.database.video_repository import VideoRepository
from app.embeddings.chunking import chunk_text
from app.embeddings.embedder import Embedder
from app.embeddings.vector_store import VectorStore


def build_vector_store():

    repo = VideoRepository()

    embedder = Embedder()

    store = VectorStore(embedder)

    for video in repo.get_all():

        if not video.transcript:
            continue

        chunks = chunk_text(
            video.video_id,
            video.transcript,
        )

        embeddings = embedder.embed_many(
            [chunk.text for chunk in chunks]
        )

        store.add(
            chunks,
            embeddings,
        )

    return store