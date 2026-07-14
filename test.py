from app.database.comment_repository import CommentRepository
from app.ingestion.comments import get_comments
from app.ingestion.search import search_videos


videos = search_videos("What is an API?")

comments = get_comments(videos[0].video_id)

print(f"Retrieved {len(comments)} comments.")

for comment in comments[:5]:
    print(comment.author)
    print(comment.text)
    print()
    
repo = CommentRepository()

for video in videos:

    comments = get_comments(video.video_id)

    repo.save_many(comments)