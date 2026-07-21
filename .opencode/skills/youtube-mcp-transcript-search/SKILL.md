---
name: youtube-mcp-transcript-search
description: Use when the user asks to search YouTube with this repo's local YouTube MCP server, fetch a video transcript, and explain or summarize the video from that transcript. Triggers include YouTube search, what is api, transcript summary, local MCP server, stdio MCP, and search_videos/get_transcript.
---

# YouTube MCP Transcript Search

Use this skill when the user wants to use the local YouTube MCP server in this repository to search YouTube, retrieve a transcript, and summarize or explain a video from that transcript.

## Constraints

- Do not modify project files unless the user explicitly asks for changes.
- Prefer the local virtualenv interpreter: `.venv/bin/python`.
- Use stdio transport unless the user explicitly asks for HTTP.
- Base explanations only on the returned transcript when the user requests a transcript-based summary.
- If the top search result has no transcript, report that and use the highest-ranked result with an available transcript.

## Server Command

Run the MCP server over stdio with:

```bash
.venv/bin/python server.py
```

Equivalent explicit transport:

```bash
.venv/bin/python server.py stdio
```

## Workflow

1. Connect to the server using the MCP stdio client.
2. Call `search_videos` with the user's query and `max_results` of at least `5`, unless the user specifies a different count.
3. Inspect results in rank order.
4. Call `get_transcript` for each candidate video using `include_full_text: true`.
5. Stop at the first result where `transcript.available` is true.
6. Return the selected video title, channel, URL, transcript availability, and a concise transcript-grounded explanation.
7. If no transcript is available for any checked result, say so and include the checked video titles/URLs.

## One-Off Client Pattern

Use a temporary inline Python script from the repo root when the MCP tools are not already exposed directly to the agent:

```bash
.venv/bin/python - <<'PY'
import asyncio
import json
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

QUERY = "what is api"
MAX_RESULTS = 5

async def main():
    params = StdioServerParameters(
        command=".venv/bin/python",
        args=["server.py"],
        cwd=".",
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            search = await session.call_tool(
                "search_videos",
                {"query": QUERY, "max_results": MAX_RESULTS},
            )
            if search.isError:
                print(json.dumps({"error": "search failed", "content": [str(c) for c in search.content]}, indent=2))
                return

            checked = []
            for video in search.structuredContent.get("videos", []):
                transcript = await session.call_tool(
                    "get_transcript",
                    {"video_id": video["video_id"], "include_full_text": True},
                )
                transcript_data = (
                    transcript.structuredContent
                    if not transcript.isError
                    else {"available": False, "error": [str(c) for c in transcript.content]}
                )
                checked.append({"video": video, "transcript": transcript_data})
                if transcript_data.get("available"):
                    break

            print(json.dumps({"checked": checked}, indent=2))

asyncio.run(main())
PY
```

Update `QUERY` for the user's requested search.

## Response Template

When a transcript is found, respond with:

```text
The top result was <title> by <channel>, but <transcript status if unavailable>.

I used the highest-ranked result with a transcript:
<title> by <channel>
<url>

<concise explanation based on transcript>
```

If the actual top result has a transcript, omit the fallback language and explain that video directly.

## Common Example

For `"what is api"`, call:

```json
{"query": "what is api", "max_results": 5}
```

Then fetch transcripts in rank order with:

```json
{"video_id": "<video_id>", "include_full_text": true}
```
