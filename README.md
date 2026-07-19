# YouTube MCP Server

MCP server for YouTube data. Search videos, resolve channels, fetch transcripts, get comments, retrieve statistics, and semantically search video transcripts via the Model Context Protocol.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file with your YouTube API key:

```
YOUTUBE_API_KEY=your_api_key_here
```

## Usage

### Stdio mode (for Claude Desktop, Cursor, VS Code)

```bash
python server.py
```

### HTTP mode (for remote/web clients)

```bash
python server.py streamable-http
```

Starts a server at `http://localhost:8000/mcp`.

## Tests

```bash
python -m unittest discover -s tests
```

The MCP tests start a local test server, connect with an MCP client, and mock YouTube API calls so they do not require `YOUTUBE_API_KEY` or spend quota.

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/absolute/path/to/Youtube-Orchestration/server.py"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `search_videos` | Search YouTube for videos matching a query |
| `get_channel` | Resolve channel metadata from a URL, handle, ID, or name |
| `get_channel_videos` | Get videos from a channel and cache them in DB |
| `get_video` | Get detailed info about a specific video |
| `get_transcript` | Get transcript for a video (cached in DB) |
| `get_comments` | Get comments for a video (cached in DB) |
| `search_video_transcript` | Semantically search one cached video transcript for query-relevant chunks |
| `ingest_video` | Full ingestion: transcript + comments into DB |
| `get_stats` | Database summary statistics |

## Semantic Transcript Search

`search_video_transcript` uses the embedding pipeline in `app/embeddings/` to find transcript chunks relevant to a natural-language query.

Typical flow:

1. Use `search_videos` to find a video and cache its metadata.
2. Use `get_transcript` to fetch and cache the transcript.
3. Use `search_video_transcript` with the video ID and a question.
4. Let the MCP client/LLM answer using the returned transcript chunks as evidence.

Example query:

```json
{
  "video_id": "abc123",
  "query": "What programming language does this video recommend for beginners?",
  "k": 5
}
```

This tool returns relevant chunks and similarity scores. It does not generate the final answer itself; the MCP host model uses the returned chunks to answer.

The first semantic search may download the `BAAI/bge-small-en-v1.5` embedding model through `sentence-transformers`.

`get_channel` and `get_channel_videos` accept:

- `@GoogleCloudTech`
- `https://www.youtube.com/@GoogleCloudTech`
- `https://www.youtube.com/@GoogleCloudTech/videos`
- `https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw`
- `Google Cloud Tech`

## Project Structure

```
Youtube-Orchestration/
├── server.py              # MCP server entry point
├── requirements.txt
├── .env
├── data/youtube.db        # SQLite database
└── app/
    ├── config.py           # Environment config
    ├── models/             # Pydantic models
    ├── database/           # SQLite repositories
    ├── ingestion/          # YouTube API fetchers
    ├── embeddings/         # Transcript chunking and vector search
    └── util/               # Logger, YouTube client
```

## Known Limitations

- Semantic search is currently scoped to one video at a time.
- Cross-video transcript search is not implemented yet.
- Tools that fetch YouTube data may spend YouTube API quota.
- `search_video_transcript` builds an in-memory index per request, which is simple but slower than a persistent vector index.
