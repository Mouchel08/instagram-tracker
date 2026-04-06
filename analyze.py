"""
Analysis engine for Instagram content.
Produces all computed insights used by the dashboard and Excel export.
"""

import json
import os
from collections import Counter

import pandas as pd

from config import DATA_DIR


def load_data() -> tuple[pd.DataFrame, dict]:
    csv_path = os.path.join(DATA_DIR, "posts_processed.csv")
    account_path = os.path.join(DATA_DIR, "account.json")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            "No data found. Run `python fetch_content.py` first to pull your Instagram data."
        )

    df = pd.read_csv(csv_path, parse_dates=["timestamp"])

    account = {}
    if os.path.exists(account_path):
        with open(account_path) as f:
            account = json.load(f)

    return df, account


# ── Overview metrics ──────────────────────────────────────────────────────────

def overview_metrics(df: pd.DataFrame, account: dict) -> dict:
    return {
        "total_posts": len(df),
        "total_likes": int(df["likes"].sum()),
        "total_comments": int(df["comments"].sum()),
        "total_saves": int(df["saves"].sum()),
        "total_shares": int(df["shares"].sum()),
        "total_impressions": int(df["impressions"].sum()),
        "total_reach": int(df["reach"].sum()),
        "avg_engagement_rate": round(df["engagement_rate"].mean(), 3),
        "median_engagement_rate": round(df["engagement_rate"].median(), 3),
        "avg_likes": round(df["likes"].mean(), 1),
        "avg_comments": round(df["comments"].mean(), 1),
        "avg_saves": round(df["saves"].mean(), 1),
        "followers": account.get("followers_count", 0),
        "following": account.get("follows_count", 0),
        "username": account.get("username", ""),
        "date_range_start": df["date"].min(),
        "date_range_end": df["date"].max(),
    }


# ── Performance by content type ───────────────────────────────────────────────

def by_content_type(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("media_type").agg(
        post_count=("post_id", "count"),
        avg_likes=("likes", "mean"),
        avg_comments=("comments", "mean"),
        avg_saves=("saves", "mean"),
        avg_shares=("shares", "mean"),
        avg_reach=("reach", "mean"),
        avg_impressions=("impressions", "mean"),
        avg_engagement_rate=("engagement_rate", "mean"),
        total_likes=("likes", "sum"),
        total_comments=("comments", "sum"),
    ).round(2).reset_index()
    grouped = grouped.sort_values("avg_engagement_rate", ascending=False)
    return grouped


# ── Top performing posts ──────────────────────────────────────────────────────

def top_posts(df: pd.DataFrame, n: int = 20, by: str = "engagement_rate") -> pd.DataFrame:
    cols = ["date", "media_type", "likes", "comments", "saves", "shares",
            "reach", "impressions", "engagement_rate", "caption", "permalink", "hashtags"]
    cols = [c for c in cols if c in df.columns]
    return df.nlargest(n, by)[cols].reset_index(drop=True)


def bottom_posts(df: pd.DataFrame, n: int = 10, by: str = "engagement_rate") -> pd.DataFrame:
    cols = ["date", "media_type", "likes", "comments", "saves", "engagement_rate", "caption", "permalink"]
    cols = [c for c in cols if c in df.columns]
    return df.nsmallest(n, by)[cols].reset_index(drop=True)


# ── Timing analysis ───────────────────────────────────────────────────────────

def best_posting_times(df: pd.DataFrame) -> dict:
    by_day = (
        df.groupby("day_of_week")["engagement_rate"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "avg_engagement_rate", "count": "post_count"})
        .round(3)
        .reset_index()
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_day["day_of_week"] = pd.Categorical(by_day["day_of_week"], categories=day_order, ordered=True)
    by_day = by_day.sort_values("day_of_week")

    by_hour = (
        df.groupby("hour")["engagement_rate"]
        .agg(["mean", "count"])
        .rename(columns={"mean": "avg_engagement_rate", "count": "post_count"})
        .round(3)
        .reset_index()
    )
    by_hour = by_hour.sort_values("hour")

    return {"by_day": by_day, "by_hour": by_hour}


def posting_frequency(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.to_datetime(df["date"])
    df["year_month"] = pd.to_datetime(df["timestamp"]).dt.to_period("M").astype(str)
    freq = (
        df.groupby("year_month")
        .agg(
            post_count=("post_id", "count"),
            avg_engagement_rate=("engagement_rate", "mean"),
            avg_likes=("likes", "mean"),
            avg_saves=("saves", "mean"),
        )
        .round(3)
        .reset_index()
    )
    return freq.sort_values("year_month")


# ── Hashtag analysis ──────────────────────────────────────────────────────────

def hashtag_performance(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        tags = [t.strip() for t in str(row.get("hashtags", "")).split(",") if t.strip()]
        for tag in tags:
            records.append({
                "hashtag": tag,
                "likes": row["likes"],
                "comments": row["comments"],
                "saves": row.get("saves", 0),
                "engagement_rate": row["engagement_rate"],
                "reach": row.get("reach", 0),
            })

    if not records:
        return pd.DataFrame()

    tag_df = pd.DataFrame(records)
    result = (
        tag_df.groupby("hashtag")
        .agg(
            uses=("hashtag", "count"),
            avg_likes=("likes", "mean"),
            avg_comments=("comments", "mean"),
            avg_saves=("saves", "mean"),
            avg_engagement_rate=("engagement_rate", "mean"),
            avg_reach=("reach", "mean"),
        )
        .round(3)
        .reset_index()
        .sort_values("avg_engagement_rate", ascending=False)
    )
    return result.reset_index(drop=True)


# ── Caption analysis ──────────────────────────────────────────────────────────

def caption_length_analysis(df: pd.DataFrame) -> pd.DataFrame:
    bins = [0, 50, 150, 300, 500, 1000, 2200]
    labels = ["Micro (<50)", "Short (50-150)", "Medium (150-300)",
              "Long (300-500)", "Very Long (500-1000)", "Max (1000+)"]
    df = df.copy()
    df["caption_bucket"] = pd.cut(df["caption_length"], bins=bins, labels=labels, right=True)
    return (
        df.groupby("caption_bucket", observed=True)
        .agg(
            post_count=("post_id", "count"),
            avg_engagement_rate=("engagement_rate", "mean"),
            avg_likes=("likes", "mean"),
            avg_saves=("saves", "mean"),
        )
        .round(3)
        .reset_index()
    )


# ── Growth over time ──────────────────────────────────────────────────────────

def engagement_trend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["week"] = df["timestamp"].dt.to_period("W").astype(str)
    return (
        df.groupby("week")
        .agg(
            avg_engagement_rate=("engagement_rate", "mean"),
            avg_reach=("reach", "mean"),
            post_count=("post_id", "count"),
        )
        .round(3)
        .reset_index()
        .sort_values("week")
    )


# ── Strategy recommendations ──────────────────────────────────────────────────

def strategy_recommendations(df: pd.DataFrame, account: dict) -> list[dict]:
    recs = []
    overview = overview_metrics(df, account)
    timing = best_posting_times(df)
    types = by_content_type(df)
    tags = hashtag_performance(df)
    cap = caption_length_analysis(df)

    # Best content type
    if not types.empty:
        best_type = types.iloc[0]
        recs.append({
            "category": "Content Type",
            "insight": f"{best_type['media_type']} posts drive the highest engagement "
                       f"({best_type['avg_engagement_rate']:.2f}% avg engagement rate)",
            "action": f"Prioritise {best_type['media_type']} content in your posting schedule.",
        })

    # Best day
    if not timing["by_day"].empty:
        best_day_row = timing["by_day"].sort_values("avg_engagement_rate", ascending=False).iloc[0]
        recs.append({
            "category": "Timing — Day",
            "insight": f"{best_day_row['day_of_week']} posts get the most engagement "
                       f"({best_day_row['avg_engagement_rate']:.2f}% avg)",
            "action": f"Schedule your best content on {best_day_row['day_of_week']}s.",
        })

    # Best hour
    valid_hours = timing["by_hour"][timing["by_hour"]["post_count"] >= 2]
    if not valid_hours.empty:
        best_hour = valid_hours.sort_values("avg_engagement_rate", ascending=False).iloc[0]
        hour_str = f"{int(best_hour['hour']):02d}:00"
        recs.append({
            "category": "Timing — Hour",
            "insight": f"Posts at {hour_str} consistently outperform other times.",
            "action": f"Post between {hour_str} and {int(best_hour['hour'])+1:02d}:00 for maximum reach.",
        })

    # Best hashtag count
    if "hashtag_count" in df.columns:
        htag_perf = df.groupby("hashtag_count")["engagement_rate"].mean()
        if not htag_perf.empty:
            best_count = htag_perf.idxmax()
            recs.append({
                "category": "Hashtags",
                "insight": f"Posts with {best_count} hashtags get the highest engagement.",
                "action": f"Aim for {max(1, best_count-2)}–{best_count+2} hashtags per post.",
            })

    # Top hashtags
    if not tags.empty:
        top_tags = tags[tags["uses"] >= 3].head(5)["hashtag"].tolist()
        if top_tags:
            recs.append({
                "category": "Hashtags",
                "insight": f"Your strongest hashtags: #{', #'.join(top_tags)}",
                "action": "Keep using these in relevant posts — they consistently drive reach.",
            })

    # Caption length
    if not cap.empty:
        best_cap = cap.sort_values("avg_engagement_rate", ascending=False).iloc[0]
        recs.append({
            "category": "Captions",
            "insight": f"{best_cap['caption_bucket']} captions drive the most engagement.",
            "action": f"Write captions in the {best_cap['caption_bucket']} range.",
        })

    # Engagement rate benchmark
    avg_er = overview["avg_engagement_rate"]
    if avg_er < 1.0:
        recs.append({
            "category": "Engagement Health",
            "insight": f"Your average engagement rate ({avg_er:.2f}%) is below the 1–3% benchmark.",
            "action": "Focus on CTAs, questions in captions, and Reels to boost engagement.",
        })
    elif avg_er >= 3.0:
        recs.append({
            "category": "Engagement Health",
            "insight": f"Your engagement rate ({avg_er:.2f}%) is excellent (above 3%).",
            "action": "Maintain consistency. Consider increasing posting frequency to grow reach.",
        })

    return recs


def run_full_analysis(df: pd.DataFrame, account: dict) -> dict:
    return {
        "overview": overview_metrics(df, account),
        "by_type": by_content_type(df),
        "top_posts": top_posts(df),
        "bottom_posts": bottom_posts(df),
        "timing": best_posting_times(df),
        "frequency": posting_frequency(df),
        "hashtags": hashtag_performance(df),
        "caption_analysis": caption_length_analysis(df),
        "engagement_trend": engagement_trend(df),
        "recommendations": strategy_recommendations(df, account),
    }
