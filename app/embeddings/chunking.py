from app.models.chunk import Chunk


def chunk_text(
    video_id: str,
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[Chunk]:

    chunks: list[Chunk] = []

    step = chunk_size - overlap

    index = 0

    for start in range(0, len(text), step):

        end = start + chunk_size

        chunk = text[start:end]

        if not chunk.strip():
            continue

        chunks.append(
            Chunk(
                chunk_id=f"{video_id}_{index}",
                video_id=video_id,
                index=index,
                text=chunk,
            )
        )

        index += 1

    return chunks