"""
Fetch all historical Instagram content with metrics and save to disk.
Run this script to pull everything from the API.
"""

import json
import os
import re
import time
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from config import DATA_DIR, MEDIA_FIELDS
from instagram_api import InstagramAPI


def extract_hashtags(caption: str) -> list[str]:
    if not caption:
        return []
    return re.findall(r"#(\w+)", caption.lower())


def extract_mentions(caption: str) -> list[str]:
    if not caption:
        return []
    return re.findall(r"@(\w+)", caption.lower())


def build_post_record(media: dict, insights: dict, account: dict) -> dict:
    caption = media.get("caption", "") or ""
    timestamp = media.get("timestamp", "")
    if timestamp:
        from dateutil import parser as dtparser
        dt = dtparser.parse(timestamp)
    else:
        dt = None

    likes = media.get("like_count", 0) or 0
    comments = media.get("comments_count", 0) or 0
    saves = insights.get("saved", 0) or 0
    impressions = insights.get("impressions", 0) or 0
    reach = insights.get("reach", 0) or 0
    shares = insights.get("shares", 0) or 0
    plays = insights.get("plays", 0) or 0
    total_interactions = insights.get("total_interactions", 0) or 0

    followers = account.get("followers_count", 1) or 1
    total_engagement = likes + comments + saves + shares
    engagement_rate = round((total_engagement / followers) * 100, 4) if followers else 0

    hashtags = extract_hashtags(caption)
    mentions = extract_mentions(caption)
    caption_word_count = len(caption.split()) if caption else 0
    has_emoji = bool(re.search(r"[^\w\s,.'\"!?#@&()-]", caption))

    return {
        # Identity
        "post_id": media.get("id"),
        "permalink": media.get("permalink", ""),
        # Timing
        "timestamp": timestamp,
        "date": dt.strftime("%Y-%m-%d") if dt else "",
        "year": dt.year if dt else None,
        "month": dt.month if dt else None,
        "month_name": dt.strftime("%B") if dt else "",
        "day_of_week": dt.strftime("%A") if dt else "",
        "hour": dt.hour if dt else None,
        # Content
        "media_type": media.get("media_type", ""),
        "caption": caption,
        "caption_length": len(caption),
        "caption_word_count": caption_word_count,
        "hashtag_count": len(hashtags),
        "hashtags": ", ".join(hashtags),
        "mention_count": len(mentions),
        "mentions": ", ".join(mentions),
        "has_emoji": has_emoji,
        # Core metrics
        "likes": likes,
        "comments": comments,
        "saves": saves,
        "shares": shares,
        "plays": plays,
        "impressions": impressions,
        "reach": reach,
        "total_interactions": total_interactions if total_interactions else total_engagement,
        # Computed metrics
        "engagement_rate": engagement_rate,
        "save_rate": round((saves / reach) * 100, 4) if reach else 0,
        "reach_rate": round((reach / followers) * 100, 4) if followers else 0,
        "comments_per_like": round(comments / likes, 4) if likes else 0,
    }


def fetch_all_content(force_refresh: bool = False) -> pd.DataFrame:
    cache_path = os.path.join(DATA_DIR, "posts_raw.json")
    account_path = os.path.join(DATA_DIR, "account.json")

    api = InstagramAPI()

    # ── Account info ──────────────────────────────────────────────────────────
    print("Fetching account info...")
    account = api.get_account_info()
    with open(account_path, "w") as f:
        json.dump(account, f, indent=2)
    print(f"Account: @{account.get('username')} | {account.get('followers_count', 0):,} followers | {account.get('media_count', 0)} posts\n")

    # ── Media list ────────────────────────────────────────────────────────────
    if os.path.exists(cache_path) and not force_refresh:
        print(f"Loading cached posts from {cache_path}")
        with open(cache_path) as f:
            all_media = json.load(f)
    else:
        print("Fetching all posts from Instagram Graph API...")
        all_media = api.get_all_media(fields=MEDIA_FIELDS)
        with open(cache_path, "w") as f:
            json.dump(all_media, f, indent=2)

    # ── Per-post insights ─────────────────────────────────────────────────────
    records = []
    insights_cache_path = os.path.join(DATA_DIR, "insights_cache.json")
    insights_cache = {}

    if os.path.exists(insights_cache_path) and not force_refresh:
        with open(insights_cache_path) as f:
            insights_cache = json.load(f)

    print(f"\nFetching insights for {len(all_media)} posts...")
    for media in tqdm(all_media, desc="Posts", unit="post"):
        media_id = media["id"]
        media_type = media.get("media_type", "IMAGE")

        if media_id not in insights_cache:
            insights = api.get_media_insights(media_id, media_type)
            insights_cache[media_id] = insights
            time.sleep(0.3)  # gentle rate limiting
        else:
            insights = insights_cache[media_id]

        record = build_post_record(media, insights, account)
        records.append(record)

    # Save insights cache
    with open(insights_cache_path, "w") as f:
        json.dump(insights_cache, f, indent=2)

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    # Save processed CSV
    csv_path = os.path.join(DATA_DIR, "posts_processed.csv")
    df.to_csv(csv_path, index=False)
    print(f"\nSaved {len(df)} posts to {csv_path}")

    return df, account


if __name__ == "__main__":
    import sys
    force = "--refresh" in sys.argv
    df, account = fetch_all_content(force_refresh=force)
    print(df[["date", "media_type", "likes", "comments", "saves", "engagement_rate"]].head(10).to_string())
