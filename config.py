import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
USER_ID = os.getenv("INSTAGRAM_USER_ID")
APP_ID = os.getenv("FACEBOOK_APP_ID")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")

BASE_URL = "https://graph.facebook.com/v18.0"
GRAPH_URL = "https://graph.facebook.com/v18.0"

# Fields to fetch for each media object
MEDIA_FIELDS = ",".join([
    "id",
    "timestamp",
    "media_type",
    "media_url",
    "permalink",
    "thumbnail_url",
    "caption",
    "like_count",
    "comments_count",
    "is_shared_to_feed",
])

# Insight metrics per post type
PHOTO_CAROUSEL_METRICS = "impressions,reach,saved,likes,comments"
VIDEO_REEL_METRICS = "impressions,reach,saved,likes,comments,shares,total_interactions,plays"

# Account-level insight metrics
ACCOUNT_METRICS = "impressions,reach,follower_count,profile_views,website_clicks"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
