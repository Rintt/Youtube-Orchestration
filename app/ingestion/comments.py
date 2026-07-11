import re
#import json
import html
from app.util.logger import info, success#, warning, error
from app.util.youtube_util import get_youtube_client
import html
from app.models.comment import Comment
from app.util.logger import info, success
from app.util.youtube_util import get_youtube_client


def get_comments(
    video_id: str,
    max_comments: int | None = None,
) -> list[Comment]:

    youtube = get_youtube_client()

    info(f"Fetching comments for video '{video_id}'...")

    comments: list[Comment] = []
    seen = set()
    discard_count = 0
    next_page_token = None
    page = 1

    while True:

        info(f"Fetching page {page}...")

        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            textFormat="plainText",
            pageToken=next_page_token,
        )

        response = request.execute()

        if not response.get("items"):
            break

        for item in response["items"]:

            top_comment = item["snippet"]["topLevelComment"]
            snippet = top_comment["snippet"]
            cleaned = clean_comment(html.unescape(snippet["textOriginal"]))
            lowercased = cleaned.lower()
            if lowercased in seen or not cleaned:
                discard_count += 1
                continue

            seen.add(lowercased)
            comments.append(
                Comment(
                    comment_id=top_comment["id"],
                    video_id=video_id,
                    author=html.unescape(snippet["authorDisplayName"]),
                    text=cleaned,
                    published_at=snippet["publishedAt"],
                    like_count=snippet["likeCount"],
                )
            )

            # Optional limit for testing
            if max_comments is not None and len(comments) >= max_comments:
                success(f"Retrieved {len(comments)} comments.")
                return comments

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

        page += 1

    success(f"Retrieved {len(comments)} comments. Discarded {discard_count}.")

    return comments

def clean_comment(text: str) -> str:
    cleaned_text = text.strip()
    cleaned_text = re.sub(r"http\S+", "", cleaned_text)
    cleaned_text = " ".join(cleaned_text.split())
    if len(cleaned_text) < 10:
        return ""
    return cleaned_text