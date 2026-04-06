"""
Streamlit dashboard for Instagram performance review and strategy.
Run: streamlit run dashboard.py
"""

import os
import subprocess
import sys

import streamlit as st

# Inject Streamlit Cloud secrets into env vars so config.py can read them
for key in ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID", "FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"]:
    if key not in os.environ:
        try:
            os.environ[key] = st.secrets[key]
        except (KeyError, FileNotFoundError):
            pass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analyze import (
    by_content_type,
    caption_length_analysis,
    engagement_trend,
    hashtag_performance,
    load_data,
    overview_metrics,
    posting_frequency,
    strategy_recommendations,
    best_posting_times,
    top_posts,
    bottom_posts,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Instagram Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    @import url('https://api.fontshare.com/v2/css?f[]=clash-display@400,500,600,700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Clash Display', 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
    }
    p, span, div, label, li {
        color: #FFFFFF !important;
    }
    .stMarkdown, .stText, [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    .stSelectbox label, .stSlider label, .stRadio label {
        color: #FFFFFF !important;
    }
    .stRadio div[role="radiogroup"] label {
        color: #FFFFFF !important;
    }
    .stDataFrame, .stDataFrame * {
        color: #FFFFFF !important;
    }
    .metric-card {
        background: #111111;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        border: 1px solid #222222;
        border-top: 3px solid #FFD10D;
    }
    .metric-label { color: #888; font-size: 12px; margin-bottom: 6px; font-family: 'Space Grotesk', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { color: #FFD10D; font-size: 26px; font-weight: 700; font-family: 'Clash Display', sans-serif; }
    .metric-sub { color: #666; font-size: 11px; margin-top: 4px; }
    .rec-card {
        background: #111111;
        border-left: 4px solid #FFD10D;
        border-radius: 4px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .rec-category { color: #FFD10D; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; }
    .rec-insight { color: #fff; font-size: 14px; margin: 6px 0 4px; }
    .rec-action { color: #004AAD; font-size: 13px; }
    .stButton > button {
        background: #FFD10D !important;
        color: #000 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 4px !important;
    }
</style>
""", unsafe_allow_html=True)

COLORS = ["#FFD10D", "#004AAD", "#FFFFFF", "#F5C400", "#003A8C", "#888888"]


# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_data():
    return load_data()


def fetch_fresh():
    with st.spinner("Pulling data from Instagram API... this may take a few minutes."):
        result = subprocess.run(
            [sys.executable, "fetch_content.py", "--refresh"],
            capture_output=True, text=True
        )
        st.cache_data.clear()
        if result.returncode == 0:
            st.success("Data refreshed successfully.")
        else:
            st.error(f"Error fetching data:\n{result.stderr}")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Instagram Tracker")
    st.markdown("---")

    try:
        df_full, account = get_data()
        data_ok = True
    except FileNotFoundError:
        data_ok = False
        df_full, account = pd.DataFrame(), {}

    if st.button("Refresh Data from Instagram", type="primary", use_container_width=True):
        fetch_fresh()
        st.rerun()

    if data_ok:
        st.markdown(f"**@{account.get('username', '?')}**")
        st.markdown(f"{account.get('followers_count', 0):,} followers · {len(df_full)} posts")
        st.markdown(f"Data from: `{df_full['date'].min()}` → `{df_full['date'].max()}`")
        st.markdown("---")

        # Filters
        st.subheader("Filters")
        media_types = ["All"] + sorted(df_full["media_type"].dropna().unique().tolist())
        selected_type = st.selectbox("Content Type", media_types)

        years = sorted(df_full["year"].dropna().unique().astype(int).tolist(), reverse=True)
        year_options = ["All"] + [str(y) for y in years]
        selected_year = st.selectbox("Year", year_options)

        top_n = st.slider("Top posts to show", 5, 50, 20)

    page = st.radio(
        "View",
        ["Overview", "Performance", "Content Types", "Timing", "Hashtags", "Strategy", "All Posts"],
        label_visibility="collapsed",
    )


# ── Guard: no data ────────────────────────────────────────────────────────────

if not data_ok:
    st.title("Instagram Tracker")
    st.warning("No data yet. Click **Refresh Data from Instagram** in the sidebar to pull your posts.")
    st.info("Make sure your `.env` file has `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID` set.\nSee `README.md` for setup instructions.")
    st.stop()


# ── Apply filters ─────────────────────────────────────────────────────────────

df = df_full.copy()
if selected_type != "All":
    df = df[df["media_type"] == selected_type]
if selected_year != "All":
    df = df[df["year"] == int(selected_year)]

if df.empty:
    st.warning("No posts match the selected filters.")
    st.stop()

overview = overview_metrics(df, account)


# ── Helper: metric card ───────────────────────────────────────────────────────

def metric_card(label, value, sub=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {'<div class="metric-sub">' + sub + '</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.title("Overview")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: metric_card("Total Posts", f"{overview['total_posts']:,}")
    with c2: metric_card("Avg Engagement", f"{overview['avg_engagement_rate']:.2f}%")
    with c3: metric_card("Total Likes", f"{overview['total_likes']:,}")
    with c4: metric_card("Total Saves", f"{overview['total_saves']:,}")
    with c5: metric_card("Total Comments", f"{overview['total_comments']:,}")
    with c6: metric_card("Total Reach", f"{overview['total_reach']:,}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Engagement Rate Over Time")
        trend = engagement_trend(df)
        if not trend.empty:
            fig = px.line(trend, x="week", y="avg_engagement_rate",
                          color_discrete_sequence=["#FFD10D"],
                          labels={"week": "", "avg_engagement_rate": "Avg ER %"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Posts per Month")
        freq = posting_frequency(df)
        if not freq.empty:
            fig = px.bar(freq, x="year_month", y="post_count",
                         color_discrete_sequence=["#004AAD"],
                         labels={"year_month": "", "post_count": "Posts"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Content Mix")
    types = by_content_type(df)
    if not types.empty:
        fig = px.pie(types, values="post_count", names="media_type",
                     color_discrete_sequence=COLORS, hole=0.4)
        fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=300)
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════

elif page == "Performance":
    st.title("Performance")

    tab1, tab2 = st.tabs(["Top Posts", "Bottom Posts"])

    with tab1:
        st.subheader(f"Top {top_n} Posts by Engagement Rate")
        top = top_posts(df, n=top_n)
        if not top.empty:
            st.dataframe(top.style.format({
                "engagement_rate": "{:.2f}%",
                "likes": "{:,.0f}",
                "comments": "{:,.0f}",
                "saves": "{:,.0f}",
                "reach": "{:,.0f}",
            }), use_container_width=True, height=500)

    with tab2:
        st.subheader("10 Lowest Performing Posts")
        bottom = bottom_posts(df, n=10)
        if not bottom.empty:
            st.dataframe(bottom.style.format({
                "engagement_rate": "{:.2f}%",
                "likes": "{:,.0f}",
                "comments": "{:,.0f}",
            }), use_container_width=True)

    st.markdown("---")
    st.subheader("Metric Distributions")
    metric = st.selectbox("Metric", ["engagement_rate", "likes", "comments", "saves", "reach"])
    fig = px.histogram(df, x=metric, nbins=40, color_discrete_sequence=["#FFD10D"],
                       labels={metric: metric.replace("_", " ").title()})
    fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=300)
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# CONTENT TYPES
# ═════════════════════════════════════════════════════════════════════════════

elif page == "Content Types":
    st.title("Content Types")
    types = by_content_type(df)

    if not types.empty:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(types, x="media_type", y="avg_engagement_rate",
                         color="media_type", color_discrete_sequence=COLORS,
                         title="Avg Engagement Rate by Type",
                         labels={"avg_engagement_rate": "Avg ER %", "media_type": ""})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(types, x="media_type", y=["avg_likes", "avg_comments", "avg_saves"],
                         barmode="group", title="Avg Metrics by Type",
                         color_discrete_sequence=COLORS,
                         labels={"value": "Count", "media_type": ""})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(types.style.format({
            "avg_engagement_rate": "{:.2f}%",
            "avg_likes": "{:.1f}",
            "avg_comments": "{:.1f}",
            "avg_saves": "{:.1f}",
            "avg_reach": "{:.0f}",
        }), use_container_width=True)

    st.markdown("---")
    st.subheader("Caption Length vs Engagement")
    cap = caption_length_analysis(df)
    if not cap.empty:
        fig = px.bar(cap, x="caption_bucket", y="avg_engagement_rate",
                     color_discrete_sequence=["#FFD10D"],
                     labels={"caption_bucket": "", "avg_engagement_rate": "Avg ER %"})
        fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=300)
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TIMING
# ═════════════════════════════════════════════════════════════════════════════

elif page == "Timing":
    st.title("Best Times to Post")
    timing = best_posting_times(df)
    freq = posting_frequency(df)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("By Day of Week")
        by_day = timing["by_day"]
        if not by_day.empty:
            fig = px.bar(by_day, x="day_of_week", y="avg_engagement_rate",
                         color="avg_engagement_rate", color_continuous_scale=[[0, "#111111"], [1, "#FFD10D"]],
                         labels={"day_of_week": "", "avg_engagement_rate": "Avg ER %"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("By Hour of Day")
        by_hour = timing["by_hour"].dropna(subset=["hour"])
        if not by_hour.empty:
            by_hour["hour_label"] = by_hour["hour"].apply(lambda h: f"{int(h):02d}:00")
            fig = px.bar(by_hour, x="hour_label", y="avg_engagement_rate",
                         color="avg_engagement_rate", color_continuous_scale=[[0, "#111111"], [1, "#004AAD"]],
                         labels={"hour_label": "", "avg_engagement_rate": "Avg ER %"})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Posting Frequency & Engagement Over Time")
    if not freq.empty:
        fig = go.Figure()
        fig.add_bar(x=freq["year_month"], y=freq["post_count"], name="Posts", marker_color="#004AAD")
        fig.add_scatter(x=freq["year_month"], y=freq["avg_engagement_rate"],
                        name="Avg ER %", mode="lines+markers",
                        line=dict(color="#FFD10D"), yaxis="y2")
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000",
            yaxis=dict(title="Post Count"),
            yaxis2=dict(title="Avg ER %", overlaying="y", side="right"),
            legend=dict(orientation="h"),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# HASHTAGS
# ═════════════════════════════════════════════════════════════════════════════

elif page == "Hashtags":
    st.title("Hashtag Performance")
    tags = hashtag_performance(df)

    if tags.empty:
        st.info("No hashtag data found in your posts.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top 20 Hashtags by Engagement Rate")
            top_tags = tags[tags["uses"] >= 2].head(20)
            fig = px.bar(top_tags, x="avg_engagement_rate", y="hashtag",
                         orientation="h", color="avg_engagement_rate",
                         color_continuous_scale=[[0, "#111111"], [1, "#FFD10D"]],
                         labels={"avg_engagement_rate": "Avg ER %", "hashtag": ""})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", showlegend=False, height=500)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Most Used Hashtags")
            most_used = tags.sort_values("uses", ascending=False).head(20)
            fig = px.bar(most_used, x="uses", y="hashtag",
                         orientation="h", color="uses",
                         color_continuous_scale=[[0, "#111111"], [1, "#004AAD"]],
                         labels={"uses": "Times Used", "hashtag": ""})
            fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", showlegend=False, height=500)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Full Hashtag Table")
        st.dataframe(tags.style.format({
            "avg_engagement_rate": "{:.2f}%",
            "avg_likes": "{:.1f}",
            "avg_comments": "{:.1f}",
            "avg_saves": "{:.1f}",
            "avg_reach": "{:.0f}",
        }), use_container_width=True, height=400)


# ═════════════════════════════════════════════════════════════════════════════
# STRATEGY
# ═════════════════════════════════════════════════════════════════════════════

elif page == "Strategy":
    st.title("Strategy Recommendations")
    st.markdown("Data-driven recommendations based on your actual Instagram performance.")

    recs = strategy_recommendations(df, account)

    if not recs:
        st.info("Not enough data for recommendations yet.")
    else:
        for rec in recs:
            st.markdown(f"""
            <div class="rec-card">
                <div class="rec-category">{rec['category']}</div>
                <div class="rec-insight">{rec['insight']}</div>
                <div class="rec-action">→ {rec['action']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Your Numbers at a Glance")
    types = by_content_type(df)
    if not types.empty:
        fig = px.scatter(types, x="post_count", y="avg_engagement_rate",
                         size="avg_reach", color="media_type",
                         color_discrete_sequence=COLORS,
                         text="media_type",
                         title="Volume vs. Engagement by Content Type",
                         labels={"post_count": "Number of Posts", "avg_engagement_rate": "Avg ER %"})
        fig.update_traces(textposition="top center")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#000000", plot_bgcolor="#000000", height=400)
        st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# ALL POSTS TABLE
# ═════════════════════════════════════════════════════════════════════════════

elif page == "All Posts":
    st.title("All Posts")

    search = st.text_input("Search captions / hashtags", "")
    if search:
        df = df[df["caption"].str.contains(search, case=False, na=False) |
                df["hashtags"].str.contains(search, case=False, na=False)]

    display_cols = [
        "date", "media_type", "likes", "comments", "saves", "shares",
        "reach", "impressions", "engagement_rate", "hashtag_count",
        "caption_length", "permalink",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[display_cols].style.format({
            "engagement_rate": "{:.2f}%",
            "likes": "{:,.0f}",
            "comments": "{:,.0f}",
            "saves": "{:,.0f}",
            "reach": "{:,.0f}",
            "impressions": "{:,.0f}",
        }),
        use_container_width=True,
        height=600,
    )
    st.caption(f"Showing {len(df)} posts")
