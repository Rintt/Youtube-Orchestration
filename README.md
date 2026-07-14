# Youtube MCP Server

MCP server for YouTube data. Search videos, fetch transcripts, get comments, and retrieve statistics via the Model Context Protocol.

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
| `ingest_video` | Full ingestion: transcript + comments into DB |
| `get_stats` | Database summary statistics |

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
    ├── embeddings/         # Vector search (not exposed as MCP tools)
    └── util/               # Logger, YouTube client
```
