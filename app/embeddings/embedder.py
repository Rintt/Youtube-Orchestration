class Embedder:

    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5",
        )

    def embed(
        self,
        text: str,
    ):
        return self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
    def embed_many(
        self,
        texts: list[str],
    ):
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=32,
            show_progress_bar=True,
        )
