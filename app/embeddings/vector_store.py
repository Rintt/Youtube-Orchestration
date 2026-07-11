import faiss
import numpy as np

from app.models.chunk import Chunk
from app.embeddings.embedder import Embedder


class VectorStore:

    def __init__(self, embedder: Embedder):

        self.embedder = embedder

        self.index = None

        self.chunks: list[Chunk] = []

    def add(
        self,
        chunks: list[Chunk],
        embeddings: np.ndarray,
    ):

        if self.index is None:

            dimension = embeddings.shape[1]

            self.index = faiss.IndexFlatIP(dimension)

        self.index.add(embeddings)

        self.chunks.extend(chunks)

    def search(
        self,
        query: str,
        k: int = 5,
    ) -> list[tuple[Chunk, float]]:

        query_embedding = self.embedder.embed(query)

        query_embedding = np.expand_dims(
            query_embedding,
            axis=0,
        )

        scores, indices = self.index.search(
            query_embedding,
            k,
        )

        results = []

        for score, index in zip(scores[0], indices[0]):

            if index == -1:
                continue

            results.append(
                (
                    self.chunks[index],
                    float(score),
                )
            )

        return results